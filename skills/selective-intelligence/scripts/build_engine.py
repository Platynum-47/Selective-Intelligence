#!/usr/bin/env python3
"""SI build engine — a compatibility facade over the authoritative LaneSession.

Plan and build are no longer a separate session store. They create/advance ONE
authoritative LaneSession (lane_session.py) and run the si.planning and si.execution
lanes through a pluggable execution backend.

The model is one backend, not a global prerequisite. A deterministic ``test`` backend
runs the same lane flow with no key (used by the kernel conformance run). A missing model
key fails only the model-requiring lane, surfaced through the compatibility route — it is
not an unconditional global stop.

Backends (SI_BACKEND): ``anthropic`` (default, needs ANTHROPIC_API_KEY) | ``test``.

Exit codes: 0 ok · 2 bad input · 3 backend/provider not available · 4 invalid session
· 5 model/worker failure. Output is a single JSON object on stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lane_session as LS  # noqa: E402

SKILL_ROOT = Path(__file__).resolve().parents[1]
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
BACKEND = os.environ.get("SI_BACKEND", "anthropic")


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


PLAN_SYSTEM = (
    read("subskills", "si-planner", "SKILL.md")
    + "\n\n---\n"
    + read("references", "first-checkpoint.md")
    + '\n\n---\nReturn ONLY JSON: {"checkpoint": "<one plain sentence + 1-3 numbered steps for '
    'the person, no jargon>", "task_plan": ["<bounded work chunk>"], "human_actions": ["<only '
    'real actions the person must take; empty if none>"], "go_no_go": "<\'go\' or the blocker>"}.'
)

WORKER_SYSTEM = (
    read("subskills", "si-worker", "SKILL.md")
    + '\n\n---\nBuild the slice as files that run together in a browser preview. Return ONLY JSON: '
    '{"files": {"index.html": "...", "style.css": "...", "script.js": "..."}, "behaviors_enabled": '
    '["..."], "proof": "<what you checked>", "open_failures": ["..."]}. Self-contained only.'
)


def backend_available(key: str) -> tuple[bool, str]:
    if BACKEND == "test":
        return True, ""
    if BACKEND == "anthropic":
        return (bool(key), "" if key else "provider_unconfigured")
    return False, "unknown_backend"


def run_backend(role: str, system: str, user: str, key: str) -> str:
    if BACKEND == "test":
        if role == "plan":
            return json.dumps(
                {
                    "checkpoint": "Plan (test backend): 1) scaffold the page, 2) wire behavior, 3) verify it renders.",
                    "task_plan": ["scaffold", "wire", "verify"],
                    "human_actions": [],
                    "go_no_go": "go",
                }
            )
        return json.dumps(
            {
                "files": {
                    "index.html": "<h1>Test build</h1><p>Produced by the deterministic backend.</p>",
                    "style.css": "body{font-family:system-ui;margin:2rem}",
                    "script.js": "",
                },
                "behaviors_enabled": ["renders a static page"],
                "proof": "deterministic test backend produced three files",
                "open_failures": [],
            }
        )
    return call_model(system, user, key, 4096 if role == "build" else 2048)


def _find(session: dict, lane_def_id: str) -> dict | None:
    for inst in session["lanes"].values():
        if inst["laneDefinitionId"] == lane_def_id:
            return inst
    return None


def cmd_plan(args: argparse.Namespace) -> int:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    ok, reason = backend_available(key)
    if not ok:
        print(json.dumps({"error": "model provider not configured", "code": reason or "provider_unconfigured"}))
        return 3
    idea = (args.idea or "").strip()
    if not idea:
        print(json.dumps({"error": "empty idea", "code": "bad_input"}))
        return 2
    session, errs = LS.compile_project(idea, ["si.planning", "si.execution"])
    if errs or session is None:
        print(json.dumps({"error": "; ".join(errs or ["compile failed"]), "code": "compile_error"}))
        return 5
    plan_inst = _find(session, "si.planning")
    LS.transition(session, plan_inst["laneInstanceId"], "running")
    try:
        raw = run_backend("plan", PLAN_SYSTEM, f"Build idea:\n{idea}", key)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        LS.transition(session, plan_inst["laneInstanceId"], "system_error")
        LS.save_session(session)
        print(json.dumps({"error": f"model call failed: {exc}", "code": "model_failure"}))
        return 5
    parsed = parse_json(raw) or {}
    LS.set_lane_outputs(
        session,
        plan_inst["laneInstanceId"],
        [{"name": "checkpoint", "value": parsed.get("checkpoint", "")}, {"name": "task_plan", "value": parsed.get("task_plan", [])}],
    )
    LS.set_lane_human_actions(session, plan_inst["laneInstanceId"], parsed.get("human_actions", []))
    LS.transition(session, plan_inst["laneInstanceId"], "verifying")
    LS.transition(session, plan_inst["laneInstanceId"], "complete")
    LS.save_session(session)
    print(
        json.dumps(
            {
                "sessionId": session["sessionId"],
                "checkpoint": parsed.get("checkpoint", ""),
                "humanActions": plan_inst.get("humanActions", []),
                "model": model_id(),
                "backend": BACKEND,
                "state": LS.global_state(session),
            }
        )
    )
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    ok, reason = backend_available(key)
    if not ok:
        print(json.dumps({"error": "model provider not configured", "code": reason or "provider_unconfigured"}))
        return 3
    session = LS.load_session((args.session or "").strip())
    if not session:
        print(json.dumps({"error": "invalid or expired session", "code": "invalid_session"}))
        return 4
    exec_inst = _find(session, "si.execution")
    if not exec_inst:
        print(json.dumps({"error": "no execution lane in session", "code": "invalid_session"}))
        return 4
    if exec_inst["status"] != "ready":
        print(json.dumps({"error": f"execution lane not ready (status {exec_inst['status']})", "code": "invalid_session"}))
        return 4
    plan_inst = _find(session, "si.planning")
    outs = {o["name"]: o["value"] for o in plan_inst.get("outputs", [])}
    checkpoint, task_plan = outs.get("checkpoint", ""), outs.get("task_plan", [])
    LS.transition(session, exec_inst["laneInstanceId"], "running")
    prompt = f"Plan checkpoint:\n{checkpoint}\n\nTask plan:\n{json.dumps(task_plan)}\n\nObjective:\n{session['objective']}"
    try:
        raw = run_backend("build", WORKER_SYSTEM, prompt, key)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        LS.transition(session, exec_inst["laneInstanceId"], "system_error")
        LS.save_session(session)
        print(json.dumps({"error": f"model call failed: {exc}", "code": "model_failure"}))
        return 5
    parsed = parse_json(raw)
    if not parsed or not isinstance(parsed.get("files"), dict):
        LS.transition(session, exec_inst["laneInstanceId"], "system_error")
        LS.save_session(session)
        print(json.dumps({"error": "worker did not return files", "code": "model_failure"}))
        return 5
    files = {k: v for k, v in parsed["files"].items() if isinstance(v, str)}
    LS.set_lane_outputs(session, exec_inst["laneInstanceId"], [{"name": "files", "value": files}])
    LS.transition(session, exec_inst["laneInstanceId"], "verifying")
    LS.transition(session, exec_inst["laneInstanceId"], "complete")
    LS.save_session(session)
    print(
        json.dumps(
            {
                "sessionId": session["sessionId"],
                "files": files,
                "humanActions": plan_inst.get("humanActions", []),
                "note": parsed.get("proof", "Build complete."),
                "model": model_id(),
                "backend": BACKEND,
                "state": LS.global_state(session),
            }
        )
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="SI build engine (facade over LaneSession)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--idea", required=True)
    p.set_defaults(func=cmd_plan)
    b = sub.add_parser("build")
    b.add_argument("--session", required=True)
    b.set_defaults(func=cmd_build)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
