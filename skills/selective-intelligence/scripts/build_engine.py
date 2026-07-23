#!/usr/bin/env python3
"""SI build engine: the authoritative plan → session → build loop.

This is the executable engine the architecture requires SI to own. It powers the
two-step build (plan, then build) using the canonical **si-planner** and **si-worker**
subskills as the system prompts — not client-local prompts — and owns the session
between the two steps. A client (e.g. the Platynum-47 gateway) calls this as a thin
subprocess; SI stays the source of truth for planning, sessions, humanActions, and the
build.

Dependency-free (stdlib urllib), matching the other SI scripts. Bring-your-own key via
`ANTHROPIC_API_KEY` (the end user's model, transported by the gateway — never stored here
beyond the process). Model id via `SI_MODEL`/`MODEL_ID`. Sessions persist to disk so the
plan and build steps — separate process calls — share one authoritative SI session.

Usage:
  ANTHROPIC_API_KEY=… python build_engine.py plan  --idea "a tip jar page"
  ANTHROPIC_API_KEY=… python build_engine.py build --session <sessionId>

Exit codes: 0 ok · 2 bad input · 3 provider not configured · 4 invalid/expired session
· 5 model/worker failure. All output is a single JSON object on stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


def session_dir() -> Path:
    d = Path(os.environ.get("SI_SESSION_DIR") or (Path(tempfile.gettempdir()) / "si-build-sessions"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def model_id() -> str:
    return os.environ.get("SI_MODEL") or os.environ.get("MODEL_ID") or "claude-sonnet-4-5"


def read(*parts: str) -> str:
    p = SKILL_ROOT.joinpath(*parts)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def call_model(system: str, user: str, key: str, max_tokens: int = 4096) -> str:
    body = json.dumps(
        {"model": model_id(), "max_tokens": max_tokens, "system": system, "messages": [{"role": "user", "content": user}]}
    ).encode("utf-8")
    req = urllib.request.Request(
        ANTHROPIC_URL,
        data=body,
        method="POST",
        headers={"x-api-key": key, "anthropic-version": ANTHROPIC_VERSION, "content-type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


def parse_json(text: str):
    text = (text or "").strip()
    try:
        return json.loads(text)
    except (ValueError, json.JSONDecodeError):
        pass
    i, j = text.find("{"), text.rfind("}")
    if i >= 0 and j > i:
        try:
            return json.loads(text[i : j + 1])
        except (ValueError, json.JSONDecodeError):
            return None
    return None


# Canonical planner/worker prompts, sourced from the subskills + doctrine, with a strict
# machine contract appended so the engine can return structured results to a gateway.
PLAN_SYSTEM = (
    read("subskills", "si-planner", "SKILL.md")
    + "\n\n---\n"
    + read("references", "first-checkpoint.md")
    + '\n\n---\nReturn ONLY JSON: {"checkpoint": "<one plain sentence + 1-3 numbered steps for '
    'the person, no jargon>", "task_plan": ["<bounded work chunk>"], "human_actions": ["<only '
    'real actions the person must take; empty if none>"], "go_no_go": "<\'go\' or the blocker>"}. '
    "No code. No headings. Plain language a non-developer reads."
)

WORKER_SYSTEM = (
    read("subskills", "si-worker", "SKILL.md")
    + '\n\n---\nBuild the slice as files that run together in a browser preview. Return ONLY JSON: '
    '{"files": {"index.html": "...", "style.css": "...", "script.js": "..."}, "behaviors_enabled": '
    '["..."], "proof": "<what you checked>", "open_failures": ["..."]}. Self-contained HTML/CSS/JS '
    "only, no external dependencies."
)


def cmd_plan(args: argparse.Namespace) -> int:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        print(json.dumps({"error": "model provider not configured", "code": "provider_unconfigured"}))
        return 3
    idea = (args.idea or "").strip()
    if not idea:
        print(json.dumps({"error": "empty idea", "code": "bad_input"}))
        return 2
    try:
        raw = call_model(PLAN_SYSTEM, f"Build idea:\n{idea}", key, 2048)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        print(json.dumps({"error": f"model call failed: {exc}", "code": "model_failure"}))
        return 5
    parsed = parse_json(raw) or {}
    sid = uuid.uuid4().hex
    session = {
        "sessionId": sid,
        "idea": idea,
        "checkpoint": parsed.get("checkpoint", ""),
        "task_plan": parsed.get("task_plan", []),
        "human_actions": parsed.get("human_actions", []),
        "go_no_go": parsed.get("go_no_go", ""),
        "model": model_id(),
        "created_at": datetime.now(UTC).isoformat(),
    }
    (session_dir() / f"{sid}.json").write_text(json.dumps(session, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "sessionId": sid,
                "checkpoint": session["checkpoint"],
                "humanActions": session["human_actions"],
                "model": model_id(),
            }
        )
    )
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        print(json.dumps({"error": "model provider not configured", "code": "provider_unconfigured"}))
        return 3
    sid = (args.session or "").strip()
    sf = session_dir() / f"{sid}.json"
    if not sid or not sf.exists():
        print(json.dumps({"error": "invalid or expired session", "code": "invalid_session"}))
        return 4
    session = json.loads(sf.read_text(encoding="utf-8"))
    prompt = (
        f"Plan checkpoint:\n{session['checkpoint']}\n\n"
        f"Task plan:\n{json.dumps(session['task_plan'])}\n\n"
        f"Original idea:\n{session['idea']}"
    )
    try:
        raw = call_model(WORKER_SYSTEM, prompt, key, 4096)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        print(json.dumps({"error": f"model call failed: {exc}", "code": "model_failure"}))
        return 5
    parsed = parse_json(raw)
    if not parsed or not isinstance(parsed.get("files"), dict):
        print(json.dumps({"error": "worker did not return files", "code": "model_failure"}))
        return 5
    files = {k: v for k, v in parsed["files"].items() if isinstance(v, str)}
    print(
        json.dumps(
            {
                "sessionId": sid,
                "files": files,
                "humanActions": session.get("human_actions", []),
                "note": parsed.get("proof", "Build complete."),
                "behaviors": parsed.get("behaviors_enabled", []),
                "open_failures": parsed.get("open_failures", []),
                "model": model_id(),
            }
        )
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="SI build engine (authoritative plan/build)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan", help="idea -> checkpoint + session + humanActions")
    p.add_argument("--idea", required=True)
    p.set_defaults(func=cmd_plan)
    b = sub.add_parser("build", help="sessionId -> files + proof")
    b.add_argument("--session", required=True)
    b.set_defaults(func=cmd_build)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
