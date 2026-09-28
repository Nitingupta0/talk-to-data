"""Auto-derived semantic layer: what the columns *mean*, fed to every prompt."""
from __future__ import annotations

import pandas as pd

_STATUS_NAMES = ("status", "state", "order_status", "payment_status")
_EXCLUDED_STATUSES = {"cancelled", "canceled", "failed", "refunded", "void", "voided", "test"}


def build_semantics(df: pd.DataFrame, profile: dict) -> dict:
    cols = profile["columns"]
    by_role = lambda role: [c["name"] for c in cols if c["role"] == role]  # noqa: E731

    rules: list[str] = []
    month_cols = [c["name"] for c in cols if c.get("is_month")]
    for mc in month_cols:
        rules.append(
            f"'{mc}' holds month names — never pd.to_datetime it. To order chronologically map the "
            "first three lowercase letters to 0-11 (jan..dec) and sort by that, then drop the helper column."
        )

    for c in cols:
        if c["name"].lower() in _STATUS_NAMES and c.get("top_values"):
            present = {str(v["value"]).lower() for v in c["top_values"]}
            excluded = sorted(present & _EXCLUDED_STATUSES)
            if excluded:
                rules.append(
                    f"Unless the user asks about them, exclude rows where '{c['name']}' is one of {excluded} "
                    "when computing totals."
                )

    for c in cols:
        if c["null_pct"] >= 5:
            rules.append(f"'{c['name']}' is {c['null_pct']}% empty — drop nulls on it before aggregating.")

    return {
        "metrics": by_role("metric"),
        "dimensions": by_role("dimension"),
        "time": by_role("time"),
        "identifiers": by_role("id"),
        "free_text": by_role("text"),
        "rules": rules,
    }


def schema_block(profile: dict, semantics: dict | None = None, max_samples: int = 4) -> str:
    """Compact, prompt-friendly description of the dataset."""
    lines = [f"Rows: {profile['rows']:,}   Columns: {profile['cols']}", "Columns:"]
    for c in profile["columns"]:
        samples = ", ".join(repr(s) for s in c["samples"][:max_samples])
        extra = ""
        if c.get("stats") and c["role"] == "metric":
            st = c["stats"]
            extra = f"; range {st.get('min')} → {st.get('max')}"
        lines.append(f"  - {c['name']!r} [{c['role']}, {c['dtype']}] e.g. {samples}{extra}")
    if semantics and semantics.get("rules"):
        lines.append("Business rules:")
        lines += [f"  - {r}" for r in semantics["rules"]]
    return "\n".join(lines)


def heuristic_suggestions(semantics: dict) -> list[str]:
    """Deterministic starter questions, used when the LLM is unavailable."""
    m = semantics["metrics"]
    d = semantics["dimensions"]
    t = semantics["time"]
    out = []
    if m and d:
        out.append(f"What is the total {m[0]} by {d[0]}?")
    if m and t:
        out.append(f"How has {m[0]} changed over {t[0]}?")
    if m and d:
        out.append(f"Which {d[-1]} has the highest average {m[-1]}?")
    if len(m) >= 2:
        out.append(f"Is there a relationship between {m[0]} and {m[1]}?")
    out.append("Give me a quick summary of this dataset")
    return out[:4]
