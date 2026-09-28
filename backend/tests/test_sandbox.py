import pandas as pd
import pytest

from app import sandbox

DF = pd.DataFrame({"region": ["N", "S", "N"], "revenue": [10, 20, 30]})


def test_runs_simple_groupby():
    res = sandbox.run("result = df.groupby('region')['revenue'].sum().reset_index()", DF)
    assert res.error is None
    assert res.value["revenue"].tolist() == [40, 20]


def test_last_expression_becomes_result_and_allowed_imports_are_dropped():
    res = sandbox.run("import pandas as pd\ndf['revenue'].sum()", DF)
    assert res.error is None and res.value == 60


def test_strips_markdown_fences():
    res = sandbox.run("```python\nresult = len(df)\n```", DF)
    assert res.value == 3


@pytest.mark.parametrize("code", [
    "import os\nresult = os.listdir('.')",
    "from pandas import io\nresult = 1",
    "result = open('/etc/passwd').read()",
    "result = ().__class__.__bases__[0].__subclasses__()",
    "result = getattr(df, 'to_csv')('x.csv')",
    "df.to_csv('/tmp/x.csv'); result = 1",
    "result = pd.read_csv('/etc/passwd')",
    "result = df.query('revenue.__class__')",
    "result = eval('1+1')",
    "while True:\n    pass",
])
def test_blocks_dangerous_code(code):
    res = sandbox.run(code, DF)
    assert res.error is not None
    assert res.value is None


def test_does_not_mutate_source_frame():
    sandbox.run("df['revenue'] = 0\nresult = 1", DF)
    assert DF["revenue"].tolist() == [10, 20, 30]


def test_reports_runtime_errors():
    res = sandbox.run("result = df['nope'].sum()", DF)
    assert "KeyError" in res.error


def test_timeout():
    res = sandbox.run("result = sum(i for i in range(10**9))", DF, timeout=0.2)
    assert "timed out" in res.error
