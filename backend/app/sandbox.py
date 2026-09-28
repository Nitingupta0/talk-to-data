"""Restricted execution of model-written pandas code.

Defence in depth:
  1. AST allow/deny checks before anything runs (imports, dunder access,
     reflection builtins, file/network I/O methods on pandas objects).
  2. A minimal builtins table and only `pd`, `np`, `math` in scope.
  3. The dataframe is a copy, so a buggy snippet can't corrupt the cached data.
  4. A wall-clock timeout so a runaway loop can't hang the request.
"""
from __future__ import annotations

import ast
import builtins
import concurrent.futures as cf
import contextlib
import io
import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from . import config

_ALLOWED_MODULES = {"pandas", "numpy", "math"}

_FORBIDDEN_NAMES = {
    "eval", "exec", "open", "compile", "__import__", "getattr", "setattr", "delattr",
    "globals", "locals", "vars", "input", "breakpoint", "help", "exit", "quit",
    "memoryview", "super", "classmethod", "staticmethod",
}

# Pandas / numpy entry points that touch the filesystem, network, or run string code.
_FORBIDDEN_ATTRS = {
    "to_csv", "to_excel", "to_pickle", "to_parquet", "to_feather", "to_hdf", "to_sql",
    "to_stata", "to_clipboard", "to_html", "to_latex", "to_xml", "to_orc", "to_gbq",
    "to_json", "to_markdown", "save", "savez", "savetxt", "load", "loadtxt", "fromfile",
    "tofile", "genfromtxt", "memmap", "eval", "system", "popen", "ctypeslib", "lib", "io",
    "testing", "compat", "api", "plotting", "options", "set_option",
}

_SAFE_BUILTINS = {
    name: getattr(builtins, name) for name in (
        "abs", "all", "any", "bool", "dict", "divmod", "enumerate", "filter", "float",
        "format", "frozenset", "int", "isinstance", "len", "list", "map", "max", "min",
        "next", "pow", "print", "range", "reversed", "round", "set", "slice", "sorted",
        "str", "sum", "tuple", "zip", "iter", "hasattr",
        "Exception", "ValueError", "KeyError", "TypeError", "IndexError", "ZeroDivisionError",
    )
} | {"True": True, "False": False, "None": None}


class SandboxError(Exception):
    pass


@dataclass
class ExecResult:
    value: Any = None
    error: str | None = None
    stdout: str = ""
    code: str = ""


def strip_code_fences(code: str) -> str:
    code = code.strip()
    if "```" in code:
        parts = code.split("```")
        # Take the first fenced block's content
        block = parts[1] if len(parts) > 1 else parts[0]
        if block.lstrip().lower().startswith("python"):
            block = block.lstrip()[6:]
        code = block
    return code.strip()


def check_code(code: str) -> ast.Module:
    """Parse and vet the code. Raises SandboxError with a user-readable reason."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise SandboxError(f"Generated code has a syntax error: {e.msg} (line {e.lineno})") from e

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mods = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            if any(m.split(".")[0] not in _ALLOWED_MODULES for m in mods) or isinstance(node, ast.ImportFrom):
                raise SandboxError(f"Blocked import of '{', '.join(mods)}'.")
        elif isinstance(node, ast.Name):
            if node.id in _FORBIDDEN_NAMES or node.id.startswith("__"):
                raise SandboxError(f"Blocked use of '{node.id}'.")
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("_"):
                raise SandboxError(f"Blocked access to private attribute '{node.attr}'.")
            if node.attr in _FORBIDDEN_ATTRS or node.attr.startswith("read_"):
                raise SandboxError(f"Blocked call to '{node.attr}' (file, network or code-eval access).")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and "__" in node.value:
            raise SandboxError("Blocked a string containing '__'.")
        elif isinstance(node, (ast.Global, ast.Nonlocal, ast.ClassDef, ast.AsyncFunctionDef, ast.Await)):
            raise SandboxError("Blocked class/global definitions.")
        elif isinstance(node, (ast.While,)):
            # Loops over data are fine; unbounded `while` loops are not needed for analysis.
            raise SandboxError("Blocked 'while' loop — use vectorised pandas operations.")
    return tree


def _ensure_result_assignment(tree: ast.Module) -> ast.Module:
    """If the code never assigns `result`, treat its final expression as the result."""
    assigns_result = any(
        isinstance(n, ast.Name) and n.id == "result" and isinstance(n.ctx, ast.Store)
        for n in ast.walk(tree)
    )
    if not assigns_result and tree.body and isinstance(tree.body[-1], ast.Expr):
        last = tree.body[-1]
        tree.body[-1] = ast.Assign(targets=[ast.Name(id="result", ctx=ast.Store())], value=last.value)
        ast.fix_missing_locations(tree)
    return tree


def _drop_allowed_imports(tree: ast.Module) -> ast.Module:
    tree.body = [n for n in tree.body if not isinstance(n, ast.Import)]
    return tree


def run(code: str, df: pd.DataFrame, extra_frames: dict[str, pd.DataFrame] | None = None,
        timeout: float | None = None) -> ExecResult:
    code = strip_code_fences(code)
    try:
        tree = check_code(code)
    except SandboxError as e:
        return ExecResult(error=str(e), code=code)

    tree = _ensure_result_assignment(_drop_allowed_imports(tree))
    compiled = compile(tree, "<analysis>", "exec")

    scope: dict[str, Any] = {
        "__builtins__": dict(_SAFE_BUILTINS),
        "pd": pd, "np": np, "math": math,
        "df": df.copy(),
    }
    for name, frame in (extra_frames or {}).items():
        scope[name] = frame.copy()

    stdout = io.StringIO()

    def _target():
        with contextlib.redirect_stdout(stdout):
            exec(compiled, scope)  # noqa: S102 — vetted above

    pool = cf.ThreadPoolExecutor(max_workers=1)
    future = pool.submit(_target)
    try:
        future.result(timeout=timeout or config.EXEC_TIMEOUT_S)
    except cf.TimeoutError:
        pool.shutdown(wait=False, cancel_futures=True)
        return ExecResult(error=f"Execution timed out after {timeout or config.EXEC_TIMEOUT_S:.0f}s.",
                          code=code)
    except Exception as e:  # the analysis itself failed
        pool.shutdown(wait=False)
        return ExecResult(error=f"{type(e).__name__}: {e}", stdout=stdout.getvalue(), code=code)
    pool.shutdown(wait=False)

    if "result" not in scope:
        return ExecResult(error="The code did not assign a variable named 'result'.",
                          stdout=stdout.getvalue(), code=code)
    return ExecResult(value=scope["result"], stdout=stdout.getvalue(), code=code)
