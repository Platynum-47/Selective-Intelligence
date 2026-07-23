#!/usr/bin/env python3
"""SI capability discovery + backend resolver.

SI is capability-first. It does not require a model API key or any specific provider
globally. It discovers whatever the user already has authenticated — agent CLIs (Codex,
Gemini, Claude), local model runtimes, service CLIs (gh), deterministic tools (git, node,
npm, python), existing environment credentials (by reference only), and human execution —
and maps lane *capability requirements* to those adapters. Only the lanes whose required
capabilities cannot be met are blocked; everything else runs.

Secrets are never copied into SI state, artifacts, logs, prompts, or evidence — env-based
adapters are reported by variable name only ("env:NAME present"), never by value.

Adapter classes: authenticated_agent_cli · authenticated_service_cli · local_model ·
existing_api_provider · deterministic_tool · human_capability · platynum_managed_provider.
The deterministic *test* backend is NOT here — it is test-only and never a production adapter.

Usage:
  python capabilities.py inventory        # what is available on this machine
  python capabilities.py resolve          # lane runnable/blocked report against the registry
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lane_registry as reg  # noqa: E402

REASONING = ["reasoning", "code_generation", "structured_output"]

# (adapterClass, adapterId, provides, kind, detectKey)
# kind: "which" -> shutil.which(detectKey); "env" -> os.environ has detectKey; "builtin" -> always
ADAPTERS = [
    ("authenticated_agent_cli", "codex", REASONING, "which", "codex"),
    ("authenticated_agent_cli", "gemini", REASONING, "which", "gemini"),
    ("authenticated_agent_cli", "claude", REASONING, "which", "claude"),
    ("local_model", "ollama", REASONING, "which", "ollama"),
    ("existing_api_provider", "anthropic-env", REASONING, "env", "ANTHROPIC_API_KEY"),
    ("existing_api_provider", "openai-env", REASONING, "env", "OPENAI_API_KEY"),
    ("authenticated_service_cli", "gh", ["git_service"], "which", "gh"),
    ("deterministic_tool", "git", ["version_control"], "which", "git"),
    ("deterministic_tool", "node", ["preview_runtime", "shell_execution"], "which", "node"),
    ("deterministic_tool", "npm", ["test_runner"], "which", "npm"),
    ("deterministic_tool", "python", ["shell_execution", "filesystem_write"], "builtin", ""),
    ("deterministic_tool", "shell", ["shell_execution", "filesystem_write"], "builtin", ""),
    ("platynum_managed_provider", "platynum", REASONING, "env", "MODEL_API_KEY"),
    ("human_capability", "human", ["human"], "builtin", ""),
]


def detect(kind: str, key: str) -> tuple[bool, str]:
    if kind == "builtin":
        return True, "builtin"
    if kind == "which":
        path = shutil.which(key)
        return (bool(path), f"which:{path}" if path else "not found on PATH")
    if kind == "env":
        # By reference only — never read or store the value.
        return (key in os.environ and bool(os.environ.get(key)), f"env:{key} present" if os.environ.get(key) else f"env:{key} absent")
    return False, "unknown detector"


def inventory() -> list[dict]:
    out = []
    for cls, aid, provides, kind, key in ADAPTERS:
        ok, evidence = detect(kind, key)
        out.append({"class": cls, "id": aid, "provides": provides, "status": "available" if ok else "unavailable", "evidence": evidence})
    return out


def available_adapters() -> list[dict]:
    return [a for a in inventory() if a["status"] == "available"]


def resolve_requirements(requirements: list[str]) -> dict:
    avail = available_adapters()
    provided = {}
    for a in avail:
        for cap in a["provides"]:
            provided.setdefault(cap, []).append(a["id"])
    missing = [c for c in requirements if c not in provided]
    # Smallest sufficient set: greedy cover of the requirements.
    selected: list[str] = []
    remaining = set(requirements) - set(missing)
    pool = sorted(avail, key=lambda a: -len(set(a["provides"]) & remaining))
    for a in pool:
        if not remaining:
            break
        covers = set(a["provides"]) & remaining
        if covers:
            selected.append(a["id"])
            remaining -= covers
    return {
        "requirements": requirements,
        "selectedAdapters": selected,
        "missingCapabilities": missing,
        "runnable": not missing,
    }


def resolve_lanes() -> dict:
    lanes, errors = reg.load_lanes()
    avail = available_adapters()
    available_caps = sorted({c for a in avail for c in a["provides"]})
    runnable, blocked, all_selected, all_missing = [], [], set(), set()
    lane_reports = {}
    for lid, m in lanes.items():
        requires = m.get("requires", [])
        r = resolve_requirements(requires)
        lane_reports[lid] = r
        if r["runnable"]:
            runnable.append(lid)
            all_selected.update(r["selectedAdapters"])
        else:
            blocked.append(lid)
            all_missing.update(r["missingCapabilities"])
    return {
        "availableCapabilities": available_caps,
        "availableAdapters": [a["id"] for a in avail],
        "selectedAdapters": sorted(all_selected),
        "missingCapabilities": sorted(all_missing),
        "runnableLaneIds": sorted(runnable),
        "blockedLaneIds": sorted(blocked),
        "lanes": lane_reports,
        "note": "A missing model capability blocks only model-requiring lanes; deterministic and independent lanes still run.",
        "errors": errors,
    }


def cmd_inventory(_a: argparse.Namespace) -> int:
    print(json.dumps({"adapters": inventory()}, indent=2))
    return 0


def cmd_resolve(_a: argparse.Namespace) -> int:
    print(json.dumps(resolve_lanes(), indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="SI capability discovery + backend resolver")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inventory", help="detect available adapters").set_defaults(func=cmd_inventory)
    sub.add_parser("resolve", help="lane runnable/blocked report").set_defaults(func=cmd_resolve)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
