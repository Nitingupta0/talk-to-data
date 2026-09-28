"""The question → answer pipeline.

    plan (1 LLM call: clarify / respond / analyze + standalone question + intent + chart hint)
      └─ for each data source:
           generate code (LLM) → vet + run in sandbox → on failure, self-repair (LLM, up to N times)
           → normalise result → pick chart → narrate from the RESULT (LLM)

`run_turn` is a generator of events so the API can stream progress to the UI.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterator

import pandas as pd

from . import config, prompts, results, sandbox
from .data import profile_frame
from .llm import LLM, LLMError
from .semantics import build_semantics, heuristic_suggestions, schema_block

MERGE_KEYWORDS = ("merge", "combine", "combined", "together", "across files", "across all files",
                  "between files", "all datasets", "both datasets", "both files", "all files")


@dataclass
class Source:
    name: str
    df: pd.DataFrame
    profile: dict
    semantics: dict
    ids: list[str] = field(default_factory=list)
    parts: list[str] = field(default_factory=list)  # original file names when merged


# ---------------------------------------------------------------------------
# Dataset welcome
# ---------------------------------------------------------------------------

def dataset_insights(llm: LLM | None, name: str, profile: dict, semantics: dict) -> dict:
    fallback = {
        "summary": f"**{name}** has {profile['rows']:,} rows and {profile['cols']} columns.",
        "suggestions": heuristic_suggestions(semantics),
    }
    if llm is None:
        return fallback
    try:
        data = llm.complete_json([
            {"role": "system", "content": prompts.WELCOME_SYSTEM},
            {"role": "user", "content": f"File: {name}\n{schema_block(profile, semantics)}"},
        ], temperature=0.4, max_tokens=400)
        suggestions = [str(s).strip() for s in data.get("suggestions", []) if str(s).strip()][:4]
        return {"summary": str(data.get("summary") or fallback["summary"]),
                "suggestions": suggestions or fallback["suggestions"]}
    except LLMError:
        return fallback


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def _history_for_llm(history: list[dict], limit: int = 8) -> list[dict]:
    out = []
    for m in history[-limit:]:
        if m["role"] == "user":
            out.append({"role": "user", "content": m.get("content", "")})
        elif m.get("kind") in ("answer", "clarify", "respond"):
            text = m.get("content", "")
            if m.get("question"):
                text = f"[Answered: {m['question']}] {text}"
            out.append({"role": "assistant", "content": text[:600]})
    return out


def plan(llm: LLM, question: str, history: list[dict], sources: list[Source]) -> dict:
    schema = "\n\n".join(f"### Dataset: {s.name}\n{schema_block(s.profile, s.semantics)}" for s in sources)
    messages = [{"role": "system", "content": prompts.PLANNER_SYSTEM + "\n\nAvailable data:\n" + schema}]
    messages += _history_for_llm(history)
    messages.append({"role": "user", "content": question})
    data = llm.complete_json(messages, temperature=0.0, max_tokens=500)

    action = data.get("action") if data.get("action") in ("analyze", "clarify", "respond") else "analyze"
    intent = data.get("intent") if data.get("intent") in prompts.INTENTS else "summary"
    chart = data.get("chart") if data.get("chart") in (*results.CHART_TYPES, "auto", "none") else "auto"
    return {
        "action": action,
        "question": str(data.get("question") or question).strip(),
        "intent": intent,
        "chart": chart,
        "clarification": str(data.get("clarification") or "").strip(),
        "reply": str(data.get("reply") or "").strip(),
    }


def _codegen_messages(question: str, intent: str, source: Source, prev_code: str | None) -> list[dict]:
    user = [
        f"Dataset: {source.name}",
        schema_block(source.profile, source.semantics),
        f"\nQuestion: {question}",
        f"Analysis type: {intent} — {prompts.INTENT_GUIDANCE.get(intent, '')}",
    ]
    if prev_code:
        user.append(f"\nCode that answered the previous question (reuse it if this is a follow-up):\n{prev_code}")
    return [{"role": "system", "content": prompts.CODEGEN_SYSTEM},
            {"role": "user", "content": "\n".join(user)}]


def _status(stage: str, label: str, source: str | None = None) -> dict:
    return {"type": "status", "stage": stage, "label": label, "source": source}


def analyze_source(llm: LLM, planned: dict, source: Source, prev_code: str | None):
    """Generate, run and (if needed) repair code for one source.

    A generator: yields status events and *returns* the result block (use `yield from`).
    """
    question, intent = planned["question"], planned["intent"]
    messages = _codegen_messages(question, intent, source, prev_code)
    block: dict = {"source": source.name, "kind": "error", "attempts": 0, "warnings": []}

    empty_retry_used = False
    max_attempts = 1 + config.MAX_REPAIR_ATTEMPTS
    outcome = None
    while block["attempts"] < max_attempts:
        block["attempts"] += 1
        yield _status("code" if block["attempts"] == 1 else "repair",
                      "Writing analysis code" if block["attempts"] == 1
                      else f"Fixing the code (attempt {block['attempts']})", source.name)
        try:
            code = sandbox.strip_code_fences(llm.complete(messages, temperature=0.0, max_tokens=1200))
        except LLMError as e:
            block["error"] = f"The language model is unavailable: {e}"
            return block

        yield _status("run", "Running it on your data", source.name)
        outcome = sandbox.run(code, source.df)
        block["code"] = outcome.code

        if outcome.error is None:
            kind, frame, scalar = results.normalize(outcome.value)
            if kind == "empty" and not empty_retry_used and block["attempts"] < max_attempts:
                empty_retry_used = True
                messages += [
                    {"role": "assistant", "content": outcome.code},
                    {"role": "user", "content": "That returned no rows. Check filter values against the sample "
                     "values in the schema (case, spacing, spelling). If empty really is correct, return the same code."},
                ]
                continue
            return _finish_block(block, kind, frame, scalar, planned, source)

        messages += [
            {"role": "assistant", "content": outcome.code},
            {"role": "user", "content": f"Running that code failed:\n{outcome.error}\n\n"
             "Fix the problem and return the full corrected code only."},
        ]

    block["error"] = outcome.error if outcome else "No code was produced."
    return block


def _finish_block(block: dict, kind: str, frame, scalar, planned: dict, source: Source) -> dict:
    cols = [c["name"] for c in source.profile["columns"]]
    block["kind"] = kind
    block["citation"] = {
        "rows_scanned": len(source.df),
        "columns_used": results.columns_used(block.get("code", ""), cols),
        "sources": source.parts or [source.name],
    }
    if block["attempts"] > 1:
        block["warnings"].append(f"Self-corrected after {block['attempts'] - 1} failed attempt(s).")
    if kind == "scalar":
        label = frame.columns[0] if frame is not None else results.scalar_label(
            block.get("code", ""), block["citation"]["columns_used"], source.semantics.get("metrics", []))
        block["scalar"] = {"value": scalar, "label": str(label or planned["question"])}
    elif kind == "table":
        block["table"] = results.table_payload(frame)
        if block["table"]["truncated"]:
            block["warnings"].append(f"Showing the first {config.MAX_RESULT_ROWS} of {len(frame):,} rows.")
        if planned["chart"] != "none":
            hint = None if planned["chart"] == "auto" else planned["chart"]
            block["chart"] = results.build_chart(frame, planned["question"], planned["intent"], hint)
    else:
        block["table"] = results.table_payload(frame) if frame is not None else None
    return block


def _result_preview(block: dict) -> str:
    if block["kind"] == "scalar":
        return f"{block['scalar']['label']}: {block['scalar']['value']}"
    table = block.get("table")
    if not table or not table["rows"]:
        return "(no rows matched)"
    frame = pd.DataFrame(table["rows"][:40], columns=table["columns"])
    note = f"\n(showing 40 of {table['total_rows']} rows)" if table["total_rows"] > 40 else ""
    return frame.to_csv(index=False) + note


def narrate(llm: LLM, question: str, block: dict) -> tuple[str, list[str]]:
    try:
        data = llm.complete_json([
            {"role": "system", "content": prompts.NARRATOR_SYSTEM},
            {"role": "user", "content": f"Question: {question}\n\nResult:\n{_result_preview(block)}"},
        ], temperature=0.2, max_tokens=500)
    except LLMError:
        return "Here's what the data shows.", []
    follow = [str(f).strip() for f in data.get("follow_ups", []) if str(f).strip()][:3]
    return str(data.get("answer") or "Here's what the data shows.").strip(), follow


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def resolve_mode(mode: str, question: str, n_sources: int) -> str:
    if n_sources <= 1:
        return "single"
    if mode in ("merge", "separate"):
        return mode
    q = question.lower()
    return "merge" if any(k in q for k in MERGE_KEYWORDS) else "separate"


def merge_sources(sources: list[Source]) -> Source:
    frames = [s.df.assign(source_file=s.name) for s in sources]
    df = pd.concat(frames, ignore_index=True, sort=False)
    profile = profile_frame(df)
    return Source(name=" + ".join(s.name for s in sources), df=df, profile=profile,
                  semantics=build_semantics(df, profile), ids=[i for s in sources for i in s.ids],
                  parts=[s.name for s in sources])


def run_turn(llm: LLM | None, question: str, history: list[dict], sources: list[Source],
             mode: str = "auto") -> Iterator[dict]:
    """Yield status events, then exactly one {'type': 'message', 'payload': ...} event."""
    started = time.time()

    def finish(payload: dict):
        payload["duration_ms"] = int((time.time() - started) * 1000)
        return {"type": "message", "payload": payload}

    if llm is None:
        yield finish({"kind": "error", "content":
                      "No language model is configured. Add `GROQ_API_KEY` to your `.env` file and restart the backend."})
        return
    if not sources:
        yield finish({"kind": "error", "content": "Attach a dataset to this chat first — upload a file or pick one from your library."})
        return

    yield _status("plan", "Understanding your question")
    try:
        planned = plan(llm, question, history, sources)
    except LLMError as e:
        yield finish({"kind": "error", "content": f"The language model request failed: {e}"})
        return

    if planned["action"] == "clarify" and planned["clarification"]:
        yield finish({"kind": "clarify", "content": planned["clarification"], "question": planned["question"]})
        return
    if planned["action"] == "respond" and planned["reply"]:
        yield finish({"kind": "respond", "content": planned["reply"], "question": planned["question"]})
        return

    resolved = resolve_mode(mode, question, len(sources))
    targets = [merge_sources(sources)] if resolved == "merge" else sources

    prev_code = None
    for m in reversed(history):
        if m.get("kind") == "answer" and m.get("results"):
            prev_code = m["results"][0].get("code")
            break

    blocks = []
    for src in targets:
        block = yield from analyze_source(llm, planned, src, prev_code if len(targets) == 1 else None)
        blocks.append(block)

    follow_ups: list[str] = []
    yield _status("explain", "Explaining the result")
    for block in blocks:
        if block["kind"] == "error":
            block["narrative"] = f"I couldn't compute this for **{block['source']}**: {block.get('error')}"
            continue
        block["narrative"], follow = narrate(llm, planned["question"], block)
        follow_ups = follow_ups or follow

    ok = [b for b in blocks if b["kind"] != "error"]
    if len(blocks) == 1:
        content = blocks[0]["narrative"]
    else:
        content = f"I answered this separately for each of your **{len(blocks)} files** — switch between them below." \
            if ok else "I couldn't answer this for any of the attached files."

    yield finish({
        "kind": "answer" if ok else "error",
        "content": content,
        "question": planned["question"],
        "intent": planned["intent"],
        "mode": resolved,
        "results": blocks,
        "follow_ups": follow_ups,
    })
