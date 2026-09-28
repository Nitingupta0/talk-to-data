"""Turn whatever the analysis code returned into a table / scalar, and pick a chart for it."""
from __future__ import annotations

import ast
import re

import numpy as np
import pandas as pd

from . import config
from .data import MONTH_LOOKUP, to_jsonable

CHART_TYPES = ("bar", "line", "area", "pie", "scatter")
_EXPLICIT = {
    "pie": "pie", "donut": "pie", "doughnut": "pie", "share": "pie",
    "line": "line", "trend": "line", "over time": "line",
    "area": "area", "stacked area": "area",
    "bar": "bar", "column": "bar", "histogram": "bar",
    "scatter": "scatter", "correlation": "scatter", "relationship": "scatter",
}
MAX_CATEGORIES = 30
MAX_SERIES = 8
MAX_PIE_SLICES = 6


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def normalize(value) -> tuple[str, pd.DataFrame | None, object]:
    """Return (kind, frame, scalar) where kind is 'table', 'scalar' or 'empty'."""
    if value is None:
        return "empty", None, None

    if isinstance(value, pd.Series):
        name = value.name if value.name is not None else "value"
        index_name = value.index.name or ("category" if name != "category" else "label")
        if isinstance(value.index, pd.RangeIndex) and value.index.name is None:
            value = value.to_frame(name=str(name))
        else:
            value = value.rename(str(name)).rename_axis(index_name).reset_index()
    elif isinstance(value, dict):
        if all(np.isscalar(v) or v is None for v in value.values()):
            value = pd.DataFrame({"metric": list(map(str, value.keys())), "value": list(value.values())})
        else:
            value = pd.DataFrame(value)
    elif isinstance(value, (list, tuple, np.ndarray, pd.Index)):
        value = pd.DataFrame({"value": list(value)})
    elif isinstance(value, pd.DataFrame):
        pass
    else:
        return "scalar", None, to_jsonable(value.item() if isinstance(value, np.generic) else value)

    df = value.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [" ".join(str(p) for p in col if str(p)) for col in df.columns]
    if not isinstance(df.index, pd.RangeIndex) or df.index.name is not None:
        df = df.reset_index()
        if "index" in df.columns and df["index"].equals(pd.Series(range(len(df)))):
            df = df.drop(columns="index")
    df.columns = [str(c) for c in df.columns]

    if df.empty:
        return "empty", df, None
    if df.shape == (1, 1):
        return "scalar", df, to_jsonable(df.iat[0, 0])
    return "table", df, None


def table_payload(df: pd.DataFrame) -> dict:
    limited = df.head(config.MAX_RESULT_ROWS)
    return {
        "columns": list(limited.columns),
        "rows": [[to_jsonable(v) for v in row] for row in limited.itertuples(index=False, name=None)],
        "total_rows": len(df),
        "truncated": len(df) > len(limited),
    }


def columns_used(code: str, columns: list[str]) -> list[str]:
    """Best-effort list of dataset columns referenced by the code."""
    colset = set(columns)
    hits: list[tuple[int, int, str]] = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in colset:
            hits.append((node.lineno, node.col_offset, node.value))
        elif isinstance(node, ast.Attribute) and node.attr in colset:
            hits.append((node.end_lineno, node.end_col_offset, node.attr))
    found: list[str] = []
    for *_, name in sorted(hits):
        if name not in found:
            found.append(name)
    return found


_AGG_LABELS = [
    (r"\.nunique\(", "Distinct {}"), (r"\.mean\(|\.avg\(", "Average {}"), (r"\.median\(", "Median {}"),
    (r"\.max\(", "Highest {}"), (r"\.min\(", "Lowest {}"), (r"\.sum\(", "Total {}"),
    (r"\.count\(|\blen\(|\.size\b|\.shape", "Count of {}"), (r"\.std\(", "Std. deviation of {}"),
]


def scalar_label(code: str, used: list[str], metrics: list[str]) -> str | None:
    """Name a bare scalar from its code, e.g. `df['revenue'].sum()` -> 'Total revenue'."""
    subject = next((c for c in reversed(used) if c in metrics), used[-1] if used else None)
    last_line = code.strip().splitlines()[-1] if code.strip() else ""
    for pattern, template in _AGG_LABELS:
        if re.search(pattern, last_line):
            return template.format(subject.replace("_", " ") if subject else "rows").strip()
    return subject.replace("_", " ").capitalize() if subject else None


# ---------------------------------------------------------------------------
# Chart selection
# ---------------------------------------------------------------------------

def requested_chart(question: str) -> str | None:
    q = question.lower()
    for kw, kind in sorted(_EXPLICIT.items(), key=lambda kv: -len(kv[0])):
        if re.search(rf"\b{re.escape(kw)}\b", q):
            return kind
    return None


def _is_time_like(s: pd.Series, name: str) -> bool:
    if pd.api.types.is_datetime64_any_dtype(s):
        return True
    if pd.api.types.is_numeric_dtype(s):
        return bool(re.search(r"year|month|quarter|week|day|date|period", name, re.I)) and s.nunique() > 2
    vals = s.dropna().astype(str).str.strip().str.lower()
    if vals.empty:
        return False
    if vals.str[:3].isin(list(MONTH_LOOKUP)).mean() > 0.9:
        return True
    return bool(vals.str.match(r"^\d{4}([-/]\d{1,2}([-/]\d{1,2})?|[-\s]?q[1-4])?$").mean() > 0.9)


def _month_sort(df: pd.DataFrame, col: str) -> pd.DataFrame:
    s = df[col]
    if pd.api.types.is_numeric_dtype(s) or pd.api.types.is_datetime64_any_dtype(s):
        return df.sort_values(col, kind="stable")
    key = s.astype(str).str.strip().str.lower().map(lambda v: MONTH_LOOKUP.get(v, MONTH_LOOKUP.get(v[:3])))
    if key.notna().mean() > 0.9:
        return df.assign(_k=key).sort_values("_k", kind="stable").drop(columns="_k")
    return df.sort_values(col, kind="stable")


def build_chart(df: pd.DataFrame, question: str, intent: str | None, hint: str | None = None) -> dict | None:
    """Return a chart spec the frontend can render, or None if a chart would not help."""
    if df is None or df.empty or len(df) < 2:
        return None

    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])]
    non_numeric = [c for c in df.columns if c not in numeric]
    if not numeric:
        return None

    x = None
    if non_numeric:
        x = next((c for c in non_numeric if _is_time_like(df[c], c)), non_numeric[0])
    elif len(numeric) >= 2:
        # All numeric: a time-like first column is an x axis; otherwise it's a scatter.
        if _is_time_like(df[numeric[0]], numeric[0]):
            x = numeric[0]
        else:
            x = numeric[0]
            return _spec("scatter", df.head(1000), x, [numeric[1]], question,
                         alternatives=["scatter"])
    else:
        return None

    series = [c for c in numeric if c != x][:MAX_SERIES]
    if not series:
        return None
    data = df[[x] + series].dropna(subset=series, how="all")
    time_x = _is_time_like(data[x], x)
    if time_x:
        data = _month_sort(data, x)

    wanted = hint if hint in CHART_TYPES else None
    wanted = requested_chart(question) or wanted

    if not time_x and len(data) > MAX_CATEGORIES:
        data = data.sort_values(series[0], ascending=False).head(MAX_CATEGORIES)

    pie_ok = len(series) == 1 and 2 <= len(data) <= 8 and (data[series[0]] >= 0).all()
    if wanted == "pie" and not pie_ok:
        wanted = None
    if wanted == "scatter" and len(series) < 1:
        wanted = None

    if wanted:
        kind = wanted
    elif time_x:
        kind = "line"
    elif intent == "breakdown" and pie_ok and len(data) <= MAX_PIE_SLICES:
        kind = "pie"
    else:
        kind = "bar"

    alternatives = ["bar", "line", "area"] + (["pie"] if pie_ok else [])
    if kind == "bar" and not time_x and kind != wanted:
        data = data.sort_values(series[0], ascending=False)
    return _spec(kind, data, x, series, question, alternatives=alternatives, time_x=time_x)


def _spec(kind: str, data: pd.DataFrame, x: str, series: list[str], question: str,
          alternatives: list[str], time_x: bool = False) -> dict:
    y_label = series[0] if len(series) == 1 else ""
    return {
        "type": kind,
        "x": x,
        "series": series,
        "x_label": x,
        "y_label": y_label,
        "time_x": time_x,
        "alternatives": sorted(set(alternatives) | {kind}, key=CHART_TYPES.index),
        "data": [
            {k: to_jsonable(v) if k != x else _x_value(v) for k, v in row.items()}
            for row in data.to_dict(orient="records")
        ],
    }


def _x_value(v):
    v = to_jsonable(v)
    return v if isinstance(v, (int, float)) else ("" if v is None else str(v))
