import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _events(resp):
    return [json.loads(line[6:]) for line in resp.text.splitlines() if line.startswith("data: ")]


def _upload(sample_csv):
    with sample_csv.open("rb") as f:
        r = client.post("/api/datasets", files=[("files", ("sales.csv", f, "text/csv"))])
    assert r.status_code == 200, r.text
    return r.json()[0]


def test_upload_attach_and_ask(store, fake_llm, sample_csv):
    ds = _upload(sample_csv)
    assert ds["rows"] == 16 and ds["insights"]["suggestions"] == ["Q1", "Q2", "Q3", "Q4"]
    assert "path" not in ds

    chat = client.post("/api/chats", json={"dataset_ids": [ds["id"]]}).json()
    assert chat["messages"][0]["kind"] == "welcome"

    fake_llm.plans.append({"action": "analyze", "question": "Total revenue by region",
                           "intent": "breakdown", "chart": "auto"})
    # First attempt fails, second succeeds -> self-repair path
    fake_llm.codes += ["result = df['Revenue'].sum()",
                       "result = df.groupby('region')['revenue'].sum().reset_index(name='total_revenue')"]
    r = client.post(f"/api/chats/{chat['id']}/messages", json={"content": "revenue by region?"})
    events = _events(r)
    stages = [e["stage"] for e in events if e["type"] == "status"]
    assert stages == ["plan", "code", "run", "repair", "run", "explain"]
    msg = next(e["message"] for e in events if e["type"] == "assistant_message")
    assert msg["kind"] == "answer"
    block = msg["results"][0]
    assert block["attempts"] == 2
    assert block["table"]["columns"] == ["region", "total_revenue"]
    assert block["chart"]["type"] in ("pie", "bar")
    assert block["citation"]["columns_used"] == ["region", "revenue"]
    assert msg["follow_ups"]

    full = client.get(f"/api/chats/{chat['id']}").json()
    assert full["title"] == "revenue by region?"
    assert [m["role"] for m in full["messages"]] == ["assistant", "user", "assistant"]


def test_clarify_and_multi_file_separate(store, fake_llm, sample_csv):
    a, b = _upload(sample_csv), _upload(sample_csv)
    chat = client.post("/api/chats", json={"dataset_ids": [a["id"], b["id"]]}).json()

    fake_llm.plans.append({"action": "clarify", "clarification": "Which metric?"})
    msg = [e for e in _events(client.post(f"/api/chats/{chat['id']}/messages", json={"content": "data"}))
           if e["type"] == "assistant_message"][0]["message"]
    assert msg["kind"] == "clarify" and msg["content"] == "Which metric?"

    fake_llm.plans.append({"action": "analyze", "question": "total revenue", "intent": "summary", "chart": "none"})
    fake_llm.codes += ["result = df['revenue'].sum()"] * 2
    msg = [e for e in _events(client.post(f"/api/chats/{chat['id']}/messages", json={"content": "total revenue"}))
           if e["type"] == "assistant_message"][0]["message"]
    assert msg["mode"] == "separate" and len(msg["results"]) == 2
    assert all(b["kind"] == "scalar" for b in msg["results"])


def test_merge_mode_adds_source_column(store, fake_llm, sample_csv):
    a, b = _upload(sample_csv), _upload(sample_csv)
    chat = client.post("/api/chats", json={"dataset_ids": [a["id"], b["id"]]}).json()
    client.patch(f"/api/chats/{chat['id']}", json={"mode": "merge"})
    fake_llm.plans.append({"action": "analyze", "question": "rows per file", "intent": "breakdown", "chart": "auto"})
    fake_llm.codes.append("result = df.groupby('source_file').size().reset_index(name='rows')")
    msg = [e for e in _events(client.post(f"/api/chats/{chat['id']}/messages", json={"content": "rows per file"}))
           if e["type"] == "assistant_message"][0]["message"]
    assert msg["mode"] == "merge"
    assert msg["results"][0]["citation"]["sources"] == ["sales.csv", "sales.csv"]
    assert msg["results"][0]["citation"]["rows_scanned"] == 32


def test_no_llm_configured(store, sample_csv):
    ds = _upload(sample_csv)
    assert ds["insights"]["suggestions"]  # heuristic fallback
    chat = client.post("/api/chats", json={"dataset_ids": [ds["id"]]}).json()
    msg = [e for e in _events(client.post(f"/api/chats/{chat['id']}/messages", json={"content": "hi"}))
           if e["type"] == "assistant_message"][0]["message"]
    assert msg["kind"] == "error" and "GROQ_API_KEY" in msg["content"]


def test_dataset_preview_and_delete(store, sample_csv):
    ds = _upload(sample_csv)
    detail = client.get(f"/api/datasets/{ds['id']}?rows=5").json()
    assert len(detail["preview"]["rows"]) == 5
    chat = client.post("/api/chats", json={"dataset_ids": [ds["id"]]}).json()
    assert client.delete(f"/api/datasets/{ds['id']}").status_code == 204
    assert client.get(f"/api/chats/{chat['id']}").json()["dataset_ids"] == []


def test_rejects_bad_extension(store):
    r = client.post("/api/datasets", files=[("files", ("x.exe", b"MZ", "application/octet-stream"))])
    assert r.status_code == 400
