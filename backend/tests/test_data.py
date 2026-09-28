from pathlib import Path

import pandas as pd

from app import data, results
from app.semantics import build_semantics


def test_profile_roles(sample_csv):
    [(name, df)] = data.read_file(sample_csv)
    prof = data.profile_frame(df)
    roles = {c["name"]: c["role"] for c in prof["columns"]}
    assert roles == {"month": "time", "region": "dimension", "product": "dimension",
                     "revenue": "metric", "units_sold": "metric", "ad_spend": "metric"}
    sem = build_semantics(df, prof)
    assert sem["time"] == ["month"]
    assert any("month names" in r for r in sem["rules"])


def test_cleans_numeric_and_date_text(tmp_path: Path):
    p = tmp_path / "t.csv"
    p.write_text('date,amount,Unnamed: 2\n2024-01-05,"$1,200.50",\n2024-02-10,(300),\n2024-03-01,15%,\n')
    [(_, df)] = data.read_file(p)
    assert list(df.columns) == ["date", "amount"]
    assert pd.api.types.is_datetime64_any_dtype(df["date"])
    assert df["amount"].tolist() == [1200.5, -300, 15]


def test_excel_multi_sheet(tmp_path: Path):
    p = tmp_path / "book.xlsx"
    with pd.ExcelWriter(p) as w:
        pd.DataFrame({"a": [1, 2]}).to_excel(w, sheet_name="One", index=False)
        pd.DataFrame({"b": [3, 4]}).to_excel(w, sheet_name="Two", index=False)
    frames = data.read_file(p)
    assert [n for n, _ in frames] == ["book.xlsx › One", "book.xlsx › Two"]


def test_normalize_variants():
    s = pd.Series([1, 2], index=pd.Index(["x", "y"], name="k"), name="v")
    kind, df, _ = results.normalize(s)
    assert kind == "table" and list(df.columns) == ["k", "v"]
    assert results.normalize(pd.DataFrame({"total": [5]}))[0] == "scalar"
    assert results.normalize(3.5) == ("scalar", None, 3.5)
    assert results.normalize(pd.DataFrame({"a": []}))[0] == "empty"


def test_chart_picks_line_for_months_and_orders_them():
    df = pd.DataFrame({"month": ["Mar", "Jan", "Feb"], "revenue": [3, 1, 2]})
    spec = results.build_chart(df, "revenue by month", "trend")
    assert spec["type"] == "line"
    assert [r["month"] for r in spec["data"]] == ["Jan", "Feb", "Mar"]


def test_chart_respects_explicit_request_and_intent():
    df = pd.DataFrame({"region": ["N", "S", "E"], "revenue": [3, 1, 2]})
    assert results.build_chart(df, "pie chart of revenue by region", "breakdown")["type"] == "pie"
    bar = results.build_chart(df, "compare revenue by region", "comparison")
    assert bar["type"] == "bar"
    assert [r["region"] for r in bar["data"]] == ["N", "E", "S"]
    assert "pie" in bar["alternatives"]


def test_chart_scatter_for_two_numeric():
    df = pd.DataFrame({"ad_spend": [1, 2, 3], "revenue": [2, 4, 7]})
    assert results.build_chart(df, "relationship", "correlation")["type"] == "scatter"


def test_columns_used():
    assert results.columns_used("df.groupby('region')['revenue'].sum()", ["region", "revenue", "x"]) == ["region", "revenue"]


def test_scalar_label():
    assert results.scalar_label("result = df.loc[df['status']=='x', 'revenue'].sum()", ["status", "revenue"], ["revenue"]) == "Total revenue"
    assert results.scalar_label("result = df['region'].nunique()", ["region"], []) == "Distinct region"
    assert results.scalar_label("result = len(df)", [], []) == "Count of rows"
