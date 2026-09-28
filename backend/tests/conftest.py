import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("TTD_STORAGE_DIR", tempfile.mkdtemp(prefix="ttd-test-"))
os.environ["GROQ_API_KEY"] = ""
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import prompts  # noqa: E402
from app.llm import LLM, set_llm  # noqa: E402
from app.store import Store, set_store  # noqa: E402


class FakeLLM(LLM):
    """Scripted model: routes on the system prompt so each pipeline stage gets its own queue."""

    def __init__(self):
        self.plans: list[dict] = []
        self.codes: list[str] = []
        self.calls: list[list[dict]] = []

    def complete(self, messages, *, json_mode=False, temperature=0.0, max_tokens=1024):
        self.calls.append(messages)
        system = messages[0]["content"]
        if system.startswith(prompts.PLANNER_SYSTEM[:40]):
            return json.dumps(self.plans.pop(0))
        if system == prompts.CODEGEN_SYSTEM:
            return self.codes.pop(0)
        if system == prompts.NARRATOR_SYSTEM:
            return json.dumps({"answer": "Revenue is **highest** in the West.",
                               "follow_ups": ["What about units?", "Trend by month?", "Top product?"]})
        if system == prompts.WELCOME_SYSTEM:
            return json.dumps({"summary": "Monthly sales.", "suggestions": ["Q1", "Q2", "Q3", "Q4"]})
        raise AssertionError("unexpected prompt")


@pytest.fixture
def fake_llm():
    llm = FakeLLM()
    set_llm(llm)
    yield llm
    set_llm(None)


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "test.db")
    set_store(s)
    return s


@pytest.fixture
def sample_csv():
    return Path(__file__).resolve().parents[1] / "sample_data" / "sales_data.csv"
