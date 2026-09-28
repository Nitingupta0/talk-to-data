"""FastAPI application: REST for datasets & chats, SSE for streaming answers."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, pipeline
from .data import SUPPORTED_EXTENSIONS, preview_rows, profile_frame, read_file
from .llm import get_llm
from .semantics import build_semantics
from .store import Store, get_store, new_id

app = FastAPI(title="Talk to Data", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])

DEFAULT_TITLE = "New analysis"


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ChatCreate(BaseModel):
    title: str | None = None
    dataset_ids: list[str] = Field(default_factory=list)


class ChatUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    mode: str | None = Field(default=None, pattern="^(auto|separate|merge)$")


class ChatDatasets(BaseModel):
    dataset_ids: list[str]


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _public_dataset(ds: dict) -> dict:
    return {k: v for k, v in ds.items() if k != "path"}


def _ingest(store: Store, path: Path, display_name: str) -> list[dict]:
    try:
        frames = read_file(path, display_name=display_name)
    except Exception as e:
        path.unlink(missing_ok=True)
        raise HTTPException(400, f"Could not read {display_name}: {e}") from e

    created = []
    llm = get_llm()
    for name, df in frames:
        sheet = name.split(" › ", 1)[1] if " › " in name else None
        profile = profile_frame(df)
        semantics = build_semantics(df, profile)
        ds = store.add_dataset(name, path, sheet, profile, semantics, df)
        insights = pipeline.dataset_insights(llm, name, profile, semantics)
        store.set_insights(ds["id"], insights)
        ds["insights"] = insights
        created.append(_public_dataset(ds))
    return created


def _chat_or_404(store: Store, chat_id: str) -> dict:
    chat = store.get_chat(chat_id)
    if not chat:
        raise HTTPException(404, "Chat not found")
    return chat


def _welcome_payload(ds: dict, n_attached: int) -> dict:
    insights = ds.get("insights") or {}
    content = f"**{ds['name']}** is ready — {ds['rows']:,} rows × {ds['cols']} columns.\n\n{insights.get('summary', '')}"
    if n_attached > 1:
        content += ("\n\nWith several files attached I'll answer **for each file separately** by default. "
                    "Switch to *Merge* in the composer (or say “combine”) to analyse them as one table.")
    return {"kind": "welcome", "content": content.strip(), "dataset_id": ds["id"],
            "follow_ups": insights.get("suggestions", [])}


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, default=str)}\n\n"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"ok": True, "llm_configured": get_llm() is not None, "model": config.LLM_MODEL}


@app.get("/api/datasets")
def list_datasets():
    return [_public_dataset(d) for d in get_store().list_datasets()]


@app.post("/api/datasets")
async def upload_datasets(files: list[UploadFile] = File(...)):
    store = get_store()
    created: list[dict] = []
    for f in files:
        name = Path(f.filename or "upload.csv").name
        ext = Path(name).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise HTTPException(400, f"{name}: unsupported file type. Use CSV, TSV, Excel, JSON or Parquet.")
        dest = config.UPLOAD_DIR / f"{new_id()}{ext}"
        size = 0
        with dest.open("wb") as out:
            while chunk := await f.read(1024 * 1024):
                size += len(chunk)
                if size > config.MAX_UPLOAD_MB * 1024 * 1024:
                    out.close()
                    dest.unlink(missing_ok=True)
                    raise HTTPException(413, f"{name} is larger than {config.MAX_UPLOAD_MB} MB.")
                out.write(chunk)
        created += _ingest(store, dest, name)
    return created


@app.get("/api/samples")
def list_samples():
    return [{"name": p.name, "size_kb": round(p.stat().st_size / 1024, 1)}
            for p in sorted(config.SAMPLE_DIR.glob("*")) if p.suffix.lower() in SUPPORTED_EXTENSIONS]


@app.post("/api/samples/{name}")
def load_sample(name: str):
    src = config.SAMPLE_DIR / Path(name).name
    if not src.is_file():
        raise HTTPException(404, "Sample not found")
    store = get_store()
    existing = [d for d in store.list_datasets() if d["name"] == src.name]
    if existing:
        return [_public_dataset(existing[0])]
    dest = config.UPLOAD_DIR / f"{new_id()}{src.suffix.lower()}"
    shutil.copy(src, dest)
    return _ingest(store, dest, src.name)


@app.get("/api/datasets/{ds_id}")
def get_dataset(ds_id: str, rows: int = 50):
    store = get_store()
    ds = store.get_dataset(ds_id)
    if not ds:
        raise HTTPException(404, "Dataset not found")
    return {**_public_dataset(ds), "preview": preview_rows(store.frame(ds_id), min(max(rows, 1), 500))}


@app.delete("/api/datasets/{ds_id}", status_code=204)
def delete_dataset(ds_id: str):
    get_store().delete_dataset(ds_id)


@app.get("/api/chats")
def list_chats():
    return get_store().list_chats()


@app.post("/api/chats")
def create_chat(body: ChatCreate):
    store = get_store()
    ids = [i for i in body.dataset_ids if store.get_dataset(i)]
    chat = store.create_chat(body.title or DEFAULT_TITLE)
    if ids:
        return set_chat_datasets(chat["id"], ChatDatasets(dataset_ids=ids))
    return {**chat, "messages": []}


@app.get("/api/chats/{chat_id}")
def get_chat(chat_id: str):
    store = get_store()
    return {**_chat_or_404(store, chat_id), "messages": store.list_messages(chat_id)}


@app.patch("/api/chats/{chat_id}")
def update_chat(chat_id: str, body: ChatUpdate):
    store = get_store()
    _chat_or_404(store, chat_id)
    title = body.title.strip() if body.title and body.title.strip() else None
    return store.update_chat(chat_id, title=title, mode=body.mode, touch=False)


@app.delete("/api/chats/{chat_id}", status_code=204)
def delete_chat(chat_id: str):
    get_store().delete_chat(chat_id)


@app.put("/api/chats/{chat_id}/datasets")
def set_chat_datasets(chat_id: str, body: ChatDatasets):
    store = get_store()
    chat = _chat_or_404(store, chat_id)
    ids = list(dict.fromkeys(i for i in body.dataset_ids if store.get_dataset(i)))
    added = [i for i in ids if i not in chat["dataset_ids"]]
    chat = store.update_chat(chat_id, dataset_ids=ids)
    for ds_id in added:
        store.add_message(chat_id, "assistant", _welcome_payload(store.get_dataset(ds_id), len(ids)))
    return {**chat, "messages": store.list_messages(chat_id)}


@app.post("/api/chats/{chat_id}/messages")
def post_message(chat_id: str, body: MessageCreate):
    store = get_store()
    chat = _chat_or_404(store, chat_id)
    history = store.list_messages(chat_id)
    question = body.content.strip()

    sources = []
    for ds_id in chat["dataset_ids"]:
        ds = store.get_dataset(ds_id)
        if ds:
            sources.append(pipeline.Source(name=ds["name"], df=store.frame(ds_id), profile=ds["profile"],
                                           semantics=ds["semantics"], ids=[ds_id]))

    user_msg = store.add_message(chat_id, "user", {"content": question})
    if chat["title"] == DEFAULT_TITLE:
        title = question if len(question) <= 48 else question[:47].rstrip() + "…"
        chat = store.update_chat(chat_id, title=title)

    def stream():
        yield _sse({"type": "user_message", "message": user_msg})
        yield _sse({"type": "chat", "chat": chat})
        try:
            for event in pipeline.run_turn(get_llm(), question, history, sources, chat["mode"]):
                if event["type"] == "message":
                    msg = store.add_message(chat_id, "assistant", event["payload"])
                    yield _sse({"type": "assistant_message", "message": msg})
                else:
                    yield _sse(event)
        except Exception as e:  # never leave the client hanging
            msg = store.add_message(chat_id, "assistant", {"kind": "error", "content": f"Something went wrong: {e}"})
            yield _sse({"type": "assistant_message", "message": msg})
        yield _sse({"type": "done"})

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---------------------------------------------------------------------------
# Serve the built React app when present (production / single-process mode)
# ---------------------------------------------------------------------------

if config.FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=config.FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        target = config.FRONTEND_DIST / path
        if path and target.is_file() and config.FRONTEND_DIST in target.resolve().parents:
            return FileResponse(target)
        return FileResponse(config.FRONTEND_DIST / "index.html")
