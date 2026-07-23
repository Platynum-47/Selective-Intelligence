#!/usr/bin/env python3
"""SI lane-instance session state — kernel #2.

Extends the authoritative SI session to hold a lane graph: LaneInstances created from
lane definitions, with status, dependency edges (resolved to instance ids), artifacts,
agents, and worktree info. The sessionId stays authoritative across every lane. Also
computes the set of ready lanes — the core signal the dependency scheduler acts on, and
the basis for global COMPLETE vs HUMAN_BLOCKED.

Dependency-free. Reuses the lane registry (kernel #1) to load definitions.

Usage:
  python lane_session.py compile --objective "..." --lanes si.planning,si.execution
  python lane_session.py ready   --session <id>
  python lane_session.py set-status --session <id> --lane <instanceId> --status complete
  python lane_session.py show    --session <id>
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lane_registry as reg  # noqa: E402

STATUSES = {
    "pending",
    "ready",
    "running",
    "waiting_dependency",
    "verifying",
    "repairing",
    "human_blocked",
    "complete",
    "system_error",
    "cancelled",
}
TERMINAL_OK = {"complete"}
MACHINE_RUNNABLE = {"pending", "ready", "running", "waiting_dependency", "verifying", "repairing"}


def sessions_dir() -> Path:
    d = Path(os.environ.get("SI_SESSION_DIR") or (Path(tempfile.gettempdir()) / "si-build-sessions"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _now() -> str:
    return datetime.now(UTC).isoformat()


def session_path(sid: str) -> Path:
    return sessions_dir() / f"{sid}.session.json"


def load_session(sid: str) -> dict | None:
    p = session_path(sid)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def save_session(session: dict) -> None:
    session["updated_at"] = _now()
    session_path(session["sessionId"]).write_text(json.dumps(session, indent=2), encoding="utf-8")


def new_session(objective: str) -> dict:
    return {
        "sessionId": uuid.uuid4().hex,
        "objective": objective,
        "lanes": {},
        "created_at": _now(),
        "updated_at": _now(),
    }


def make_instance(lane_def: dict) -> dict:
    iso = lane_def.get("isolationPolicy", {})
    return {
        "laneInstanceId": uuid.uuid4().hex,
        "laneDefinitionId": lane_def["id"],
        "laneVersion": lane_def["version"],
        "parentLaneId": None,
        "childLaneIds": [],
        "dependencyLaneIds": [],
        "status": "pending",
        "selectedContext": [],
        "assumptions": [],
        "assignedAgents": [],
        "branch": None,
        "worktreePath": None,
        "writableScopes": iso.get("writableScopes", []),
        "requiresWorktree": bool(iso.get("requiresWorktree", False)),
        "inputs": [],
        "outputs": [],
        "currentTask": None,
        "attempts": [],
        "verificationResults": [],
        "humanActions": [],
        "createdAt": _now(),
        "updatedAt": _now(),
        "completedAt": None,
    }


def compile_project(objective: str, lane_ids: list[str]) -> tuple[dict | None, list[str]]:
    lanes, errors = reg.load_lanes()
    if errors:
        return None, errors
    missing = [lid for lid in lane_ids if lid not in lanes]
    if missing:
        return None, [f"unknown lane(s): {', '.join(missing)}"]
    session = new_session(objective)
    # One instance per requested lane definition.
    def_to_instance: dict[str, str] = {}
    for lid in lane_ids:
        inst = make_instance(lanes[lid])
        session["lanes"][inst["laneInstanceId"]] = inst
        def_to_instance[lid] = inst["laneInstanceId"]
    # Resolve definition-level dependencies to instance ids within this session.
    for inst in session["lanes"].values():
        dep_defs = lanes[inst["laneDefinitionId"]].get("dependencies", [])
        inst["dependencyLaneIds"] = [def_to_instance[d] for d in dep_defs if d in def_to_instance]
    recompute_ready(session)
    return session, []


def recompute_ready(session: dict) -> None:
    lanes = session["lanes"]
    for inst in lanes.values():
        if inst["status"] not in ("pending", "waiting_dependency"):
            continue
        deps = inst["dependencyLaneIds"]
        if all(lanes.get(d, {}).get("status") in TERMINAL_OK for d in deps):
            inst["status"] = "ready"
        else:
            inst["status"] = "waiting_dependency"


def ready_lanes(session: dict) -> list[dict]:
    return [i for i in session["lanes"].values() if i["status"] == "ready"]


def global_state(session: dict) -> str:
    lanes = list(session["lanes"].values())
    if lanes and all(i["status"] == "complete" for i in lanes):
        return "COMPLETE"
    if any(i["status"] in MACHINE_RUNNABLE and i["status"] != "waiting_dependency" for i in lanes):
        return "RUNNING"
    if any(i["status"] == "ready" for i in lanes):
        return "RUNNING"
    # No runnable machine lane remains.
    if any(i["status"] == "human_blocked" for i in lanes):
        return "HUMAN_BLOCKED"
    if any(i["status"] == "waiting_dependency" for i in lanes):
        return "STUCK"  # deps can never resolve (e.g., a blocked upstream)
    return "RUNNING"


def cmd_compile(args: argparse.Namespace) -> int:
    lane_ids = [x.strip() for x in args.lanes.split(",") if x.strip()]
    session, errors = compile_project(args.objective, lane_ids)
    if errors:
        print(json.dumps({"error": "; ".join(errors)}))
        return 1
    save_session(session)
    print(json.dumps({"sessionId": session["sessionId"], "lanes": _summary(session), "state": global_state(session)}))
    return 0


def cmd_ready(args: argparse.Namespace) -> int:
    session = load_session(args.session)
    if not session:
        print(json.dumps({"error": "session not found"}))
        return 4
    recompute_ready(session)
    save_session(session)
    print(json.dumps({"ready": [{"laneInstanceId": i["laneInstanceId"], "lane": i["laneDefinitionId"]} for i in ready_lanes(session)], "state": global_state(session)}))
    return 0


def cmd_set_status(args: argparse.Namespace) -> int:
    session = load_session(args.session)
    if not session:
        print(json.dumps({"error": "session not found"}))
        return 4
    if args.status not in STATUSES:
        print(json.dumps({"error": f"invalid status; one of {sorted(STATUSES)}"}))
        return 2
    inst = session["lanes"].get(args.lane)
    if not inst:
        print(json.dumps({"error": "lane instance not found"}))
        return 4
    inst["status"] = args.status
    inst["updatedAt"] = _now()
    if args.status == "complete":
        inst["completedAt"] = _now()
    recompute_ready(session)
    save_session(session)
    print(json.dumps({"ok": True, "state": global_state(session), "lanes": _summary(session)}))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    session = load_session(args.session)
    if not session:
        print(json.dumps({"error": "session not found"}))
        return 4
    print(json.dumps({"sessionId": session["sessionId"], "objective": session["objective"], "state": global_state(session), "lanes": _summary(session)}, indent=2))
    return 0


def _summary(session: dict) -> list[dict]:
    return [
        {"laneInstanceId": i["laneInstanceId"], "lane": i["laneDefinitionId"], "status": i["status"], "deps": i["dependencyLaneIds"]}
        for i in session["lanes"].values()
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="SI lane-instance session state")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compile")
    c.add_argument("--objective", required=True)
    c.add_argument("--lanes", required=True, help="comma-separated lane definition ids")
    c.set_defaults(func=cmd_compile)
    r = sub.add_parser("ready")
    r.add_argument("--session", required=True)
    r.set_defaults(func=cmd_ready)
    s = sub.add_parser("set-status")
    s.add_argument("--session", required=True)
    s.add_argument("--lane", required=True)
    s.add_argument("--status", required=True)
    s.set_defaults(func=cmd_set_status)
    sh = sub.add_parser("show")
    sh.add_argument("--session", required=True)
    sh.set_defaults(func=cmd_show)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
