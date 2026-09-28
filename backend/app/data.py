"""Loading, cleaning and profiling tabular files."""
from __future__ import annotations

import io
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
MONTH_LOOKUP = {m: i for i, m in enumerate(MONTHS)} | {
    full: i for i, full in enumerate(
        ["january", "february", "march", "april", "may", "june", "july",
         "august", "september", "october", "november", "december"])
}
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

_TIME_NAME = re.compile(r"(^|_|\b)(date|time|timestamp|day|week|month|quarter|year|period|dt)($|_|\b)", re.I)
_ID_NAME = re.compile(r"(^id$|_id$|^id_|uuid|guid)", re.I)
_NUMERIC_STR = re.compile(r"^\s*[-+(]?\s*[$€£₹¥]?\s*-?[\d,]*\.?\d+\s*%?\s*\)?\s*$")

SUPPORTED_EXTENSIONS = {".csv", ".tsv", ".txt", ".xlsx", ".xlsm", ".xls", ".json", ".parquet"}


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def read_file(path: Path, display_name: str | None = None) -> list[tuple[str, pd.DataFrame]]:
    """Read a file into one or more (name, dataframe) pairs.

    Excel workbooks with several non-empty sheets yield one dataset per sheet.
    """
    name = display_name or path.name
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type '{ext}'. Use CSV, TSV, Excel, JSON or Parquet.")

    if ext in {".xlsx", ".xlsm", ".xls"}:
        sheets = pd.read_excel(path, sheet_name=None)
        frames = [(s, df) for s, df in sheets.items() if not df.dropna(how="all").empty]
        if not frames:
            raise ValueError("The workbook has no data.")
        if len(frames) == 1:
            return [(name, clean_frame(frames[0][1]))]
        return [(f"{name} › {sheet}", clean_frame(df)) for sheet, df in frames]

    if ext == ".json":
        df = pd.read_json(path)
    elif ext == ".parquet":
        df = pd.read_parquet(path)
    else:
        df = _read_delimited(path, sep="\t" if ext == ".tsv" else None)

    if df.empty:
        raise ValueError("The file has no rows.")
    return [(name, clean_frame(df))]


def _read_delimited(path: Path, sep: str | None) -> pd.DataFrame:
    raw = path.read_bytes()
    last_err: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError as e:
            last_err = e
            continue
        try:
            return pd.read_csv(io.StringIO(text), sep=sep, engine="python")
        except Exception as e:  # malformed delimiters etc.
            last_err = e
    raise ValueError(f"Could not parse the file: {last_err}")


def clean_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise headers and coerce obviously-typed text columns."""
    df = df.dropna(how="all").dropna(axis=1, how="all").copy()
    df.columns = _dedupe([_clean_header(c, i) for i, c in enumerate(df.columns)])
    for col in df.columns:
        if _is_text(df[col]):
            df[col] = _coerce_text_column(df[col])
    return df.reset_index(drop=True)


def _clean_header(col, i: int) -> str:
    s = str(col).strip()
    if not s or s.lower().startswith("unnamed:"):
        return f"column_{i + 1}"
    return re.sub(r"\s+", " ", s)


def _dedupe(cols: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    out = []
    for c in cols:
        if c in seen:
            seen[c] += 1
            out.append(f"{c}_{seen[c]}")
        else:
            seen[c] = 0
            out.append(c)
    return out


def _is_text(s: pd.Series) -> bool:
    return s.dtype == object or pd.api.types.is_string_dtype(s.dtype)


def _coerce_text_column(s: pd.Series) -> pd.Series:
    stripped = s.astype("string").str.strip()
    non_null = stripped.dropna()
    non_null = non_null[non_null != ""]
    if non_null.empty:
        return s

    # Numbers stored as text: "1,200", "$45.00", "12%", "(300)"
    if non_null.str.match(_NUMERIC_STR).mean() >= 0.95:
        cleaned = (stripped.str.replace(r"[,$€£₹¥%\s]", "", regex=True)
                   .str.replace(r"^\((.*)\)$", r"-\1", regex=True))
        converted = pd.to_numeric(cleaned, errors="coerce")
        if converted.notna().sum() >= 0.95 * len(non_null):
            return converted

    # Month / weekday names stay as text — they get an explicit ordering hint instead.
    lowered = non_null.str.lower().str[:3]
    if lowered.isin(MONTHS + WEEKDAYS).mean() > 0.9:
        return stripped

    # Date-like strings
    if non_null.str.contains(r"\d").mean() > 0.9 and non_null.str.len().median() >= 6:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            parsed = pd.to_datetime(stripped, errors="coerce", format="mixed")
        if parsed.notna().sum() >= 0.9 * len(non_null):
            return parsed

    return s


# ---------------------------------------------------------------------------
# Profiling
# ---------------------------------------------------------------------------

def is_month_column(s: pd.Series) -> bool:
    if not _is_text(s):
        return False
    vals = s.dropna().astype(str).str.strip().str.lower()
    return not vals.empty and vals.str[:3].isin(MONTHS).mean() > 0.9


def column_role(name: str, s: pd.Series, n_rows: int) -> str:
    """Classify a column as time / metric / dimension / id / text."""
    nunique = s.nunique(dropna=True)
    if pd.api.types.is_datetime64_any_dtype(s) or is_month_column(s):
        return "time"
    if pd.api.types.is_bool_dtype(s):
        return "dimension"
    if pd.api.types.is_numeric_dtype(s):
        if _ID_NAME.search(name) and nunique >= 0.9 * max(n_rows, 1):
            return "id"
        if _TIME_NAME.search(name) and pd.api.types.is_integer_dtype(s) and nunique <= 200:
            return "time"
        return "metric"
    if _ID_NAME.search(name) and nunique >= 0.9 * max(n_rows, 1):
        return "id"
    if nunique <= 50 or nunique <= 0.5 * max(n_rows, 1):
        return "dimension"
    return "text"


def to_jsonable(v):
    """Convert numpy / pandas scalars into plain JSON types."""
    if v is None:
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        f = float(v)
        return None if np.isnan(f) or np.isinf(f) else f
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, (pd.Timestamp,)):
        if pd.isna(v):
            return None
        return v.isoformat() if (v.hour or v.minute or v.second) else v.date().isoformat()
    if isinstance(v, (pd.Timedelta,)):
        return str(v)
    if v is pd.NaT or v is pd.NA:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return v


def profile_frame(df: pd.DataFrame) -> dict:
    n_rows = len(df)
    columns = []
    for col in df.columns:
        s = df[col]
        role = column_role(col, s, n_rows)
        nulls = int(s.isna().sum())
        info = {
            "name": col,
            "dtype": str(s.dtype),
            "role": role,
            "nulls": nulls,
            "null_pct": round(100 * nulls / n_rows, 1) if n_rows else 0.0,
            "unique": int(s.nunique(dropna=True)),
            "samples": [to_jsonable(v) for v in s.dropna().unique()[:5]],
        }
        if role == "time" and is_month_column(s):
            info["is_month"] = True
        if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
            desc = s.describe()
            info["stats"] = {k: to_jsonable(desc.get(k)) for k in ("min", "max", "mean", "50%")}
            info["stats"]["sum"] = to_jsonable(s.sum())
        elif pd.api.types.is_datetime64_any_dtype(s):
            info["stats"] = {"min": to_jsonable(s.min()), "max": to_jsonable(s.max())}
        if role in ("dimension", "time") and not pd.api.types.is_datetime64_any_dtype(s):
            vc = s.value_counts(dropna=True).head(6)
            info["top_values"] = [{"value": to_jsonable(k), "count": int(v)} for k, v in vc.items()]
        columns.append(info)

    return {
        "rows": n_rows,
        "cols": len(df.columns),
        "columns": columns,
        "memory_kb": round(df.memory_usage(deep=True).sum() / 1024, 1),
    }


def preview_rows(df: pd.DataFrame, n: int = 50) -> dict:
    head = df.head(n)
    return {
        "columns": list(map(str, head.columns)),
        "rows": [[to_jsonable(v) for v in row] for row in head.itertuples(index=False, name=None)],
        "total_rows": len(df),
    }
