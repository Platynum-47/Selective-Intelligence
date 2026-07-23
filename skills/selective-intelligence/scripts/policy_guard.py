#!/usr/bin/env python3
"""Pre-adapter authorization and evidence capture for SI tool execution."""
from __future__ import annotations

import hashlib
import os
import shlex
import re
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence


class PolicyDenied(PermissionError):
    def __init__(self, decision: dict[str, Any]):
        super().__init__(decision["reason"])
        self.decision = decision


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _resolved(path: str | os.PathLike[str]) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


_MUTATING_GIT = {
    "add", "am", "apply", "branch", "checkout", "cherry-pick", "clean", "commit",
    "fetch", "merge", "mv", "pull", "push", "rebase", "reset", "restore", "revert",
    "rm", "stash", "switch", "tag", "worktree",
}
_INSTALLERS = {
    ("npm", "install"), ("npm", "i"), ("pnpm", "install"), ("pnpm", "add"),
    ("yarn", "add"), ("yarn", "install"), ("pip", "install"), ("pip3", "install"),
    ("poetry", "add"), ("uv", "add"), ("cargo", "install"),
}
_DEPLOY_WORDS = {"deploy", "publish", "release"}
_WINDOWS_EXECUTABLE_SUFFIXES = (".exe", ".cmd", ".bat", ".com", ".ps1")
_TRANSPARENT_WRAPPERS = {"env", "command", "nice", "nohup", "timeout", "stdbuf", "sudo", "doas"}


def _command_basename(token: str) -> str:
    """Return a platform-normalized command basename without Windows suffixes."""
    name = Path(token).name.lower()
    for suffix in _WINDOWS_EXECUTABLE_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _skip_wrapper_prefix(base: str, argv: list[str]) -> list[str] | None:
    """Return argv with one transparent wrapper removed, or None if not unwrapable."""
    if not argv or _command_basename(argv[0]) != base:
        return None
    rest = argv[1:]

    if base == "env":
        index = 0
        while index < len(rest):
            token = rest[index]
            if token == "--":
                return rest[index + 1 :]
            if token in {"-i", "-0", "-v", "-S"}:
                index += 1
                continue
            if token in {"-u", "-C", "-P"}:
                index += 2
                continue
            if token.startswith("-"):
                index += 1
                continue
            if "=" in token and not token.startswith("-"):
                index += 1
                continue
            return rest[index:]
        return []

    if base == "command":
        index = 0
        while index < len(rest):
            token = rest[index]
            if token in {"-p", "-v", "-V"}:
                index += 1
                continue
            if token == "--":
                return rest[index + 1 :]
            if token.startswith("-"):
                index += 1
                continue
            return rest[index:]
        return []

    if base == "nice":
        index = 0
        if index < len(rest) and rest[index] in {"-n", "--adjustment"}:
            index += 2
        elif index < len(rest) and re.fullmatch(r"-?\d+", rest[index] or ""):
            index += 1
        return rest[index:]

    if base == "nohup":
        return rest[1:] if rest[:1] == ["--"] else rest

    if base == "timeout":
        index = 0
        while index < len(rest):
            token = rest[index]
            if token in {"-s", "--signal", "-k", "--kill-after"}:
                index += 2
                continue
            if token in {"--preserve-status", "--foreground", "-v", "--verbose"}:
                index += 1
                continue
            if token.startswith("-"):
                index += 1
                continue
            # duration token then command
            return rest[index + 1 :]
        return []

    if base == "stdbuf":
        index = 0
        while index < len(rest):
            token = rest[index]
            if token in {"-i", "-o", "-e", "--input", "--output", "--error"}:
                index += 2
                continue
            if token.startswith("-"):
                index += 1
                continue
            return rest[index:]
        return []

    if base in {"sudo", "doas"}:
        index = 0
        value_options = {
            "-u", "-g", "-h", "-C", "-D", "-R", "-p", "-b",
            "--user", "--group", "--host", "--chdir", "--chroot", "--prompt",
        }
        while index < len(rest):
            token = rest[index]
            if token == "--":
                return rest[index + 1 :]
            if token in value_options:
                index += 2
                continue
            if token.startswith("-"):
                index += 1
                continue
            return rest[index:]
        return []

    return None


def _resolve_command_argv(argv: Sequence[str]) -> list[str]:
    """Peel transparent wrappers and keep the effective command argv."""
    current = [str(token) for token in argv]
    # Bound unwrap depth to avoid pathological wrapper chains.
    for _ in range(32):
        if not current:
            return current
        base = _command_basename(current[0])
        if base not in _TRANSPARENT_WRAPPERS:
            return current
        unwrapped = _skip_wrapper_prefix(base, current)
        if unwrapped is None or unwrapped == current:
            return current
        current = list(unwrapped)
    return current


def _git_subcommand(argv: list[str]) -> str | None:
    """Return the Git subcommand after global options such as ``-C``/``-c``."""
    index = 1
    options_with_value = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"}
    while index < len(argv):
        token = argv[index]
        if token in options_with_value:
            index += 2
            continue
        if any(token.startswith(prefix + "=") for prefix in options_with_value if prefix.startswith("--")):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        return token.lower()
    return None


def _install_requested(base: str, argv: list[str]) -> bool:
    tokens = [token.lower() for token in argv[1:]]
    if base in {"npm", "pnpm", "yarn", "pip", "pip3", "poetry", "uv", "cargo"}:
        return any(token in {"install", "add", "i"} for token in tokens)
    if base in {"python", "python3", "py"} or base.startswith("python"):
        try:
            module_index = tokens.index("-m")
        except ValueError:
            return False
        return (
            module_index + 1 < len(tokens)
            and tokens[module_index + 1] in {"pip", "pip3"}
            and any(token == "install" for token in tokens[module_index + 2 :])
        )
    return False


def _payload_policy_violation(payload: str) -> str | None:
    normalized = " ".join(payload.lower().split())
    if re.search(r"\bgit(?:\.exe)?\b.*\b(?:" + "|".join(sorted(_MUTATING_GIT)) + r")\b", normalized):
        return "nested shell command requests Git mutation"
    if re.search(
        r"\b(?:npm(?:\.cmd|\.ps1)?|pnpm|yarn|pip3?|poetry|uv|cargo)\b.*\b(?:install|add)\b",
        normalized,
    ):
        return "nested shell command requests dependency installation"
    if re.search(r"\b(?:deploy|publish|release)\b", normalized):
        return "nested shell command requests deployment or publishing"
    return None


def _nested_shell_violation(base: str, argv: list[str]) -> str | None:
    payload: str | None = None
    lowered = [token.lower() for token in argv]
    if base in {"sh", "bash", "zsh", "fish"} and "-c" in lowered:
        idx = lowered.index("-c")
        payload = argv[idx + 1] if idx + 1 < len(argv) else ""
    elif base == "cmd" and "/c" in lowered:
        idx = lowered.index("/c")
        payload = " ".join(argv[idx + 1 :])
    elif base in {"powershell", "pwsh"}:
        for marker in ("-command", "-c"):
            if marker in lowered:
                idx = lowered.index(marker)
                payload = " ".join(argv[idx + 1 :])
                break
    elif base in {"python", "python3", "py"} and "-c" in lowered:
        idx = lowered.index("-c")
        payload = argv[idx + 1] if idx + 1 < len(argv) else ""
    elif base in {"node", "nodejs"} and ("-e" in lowered or "--eval" in lowered):
        marker = "-e" if "-e" in lowered else "--eval"
        idx = lowered.index(marker)
        payload = argv[idx + 1] if idx + 1 < len(argv) else ""
    if payload is None:
        return None
    return _payload_policy_violation(payload)


class PolicyGuard:
    """Authorizes an action before an adapter is called.

    ``canonical_roots`` are protected. Writes are allowed only inside
    ``writable_roots``. Command execution can occur in a writable root, but
    explicit constraints still deny Git mutation, installs, deploys, or other
    configured operations.
    """

    def __init__(
        self,
        *,
        canonical_roots: Sequence[str | os.PathLike[str]],
        writable_roots: Sequence[str | os.PathLike[str]],
        prohibit_git_mutation: bool = True,
        prohibit_dependency_install: bool = True,
        prohibit_deploy: bool = True,
    ) -> None:
        self.canonical_roots = tuple(_resolved(p) for p in canonical_roots)
        self.writable_roots = tuple(_resolved(p) for p in writable_roots)
        self.prohibit_git_mutation = prohibit_git_mutation
        self.prohibit_dependency_install = prohibit_dependency_install
        self.prohibit_deploy = prohibit_deploy

    def _decision(
        self,
        *,
        session_id: str,
        task_id: str,
        action: dict[str, Any],
        allowed: bool,
        reason: str,
        constraint: str,
    ) -> dict[str, Any]:
        return {
            "decisionId": _id("policy"),
            "timestamp": _now(),
            "sessionId": session_id,
            "taskId": task_id,
            "requestedOperation": action,
            "relevantConstraint": constraint,
            "decision": "ALLOW" if allowed else "DENY",
            "allowed": allowed,
            "reason": reason,
            "adapterInvocationStatus": "PENDING" if allowed else "NOT_INVOKED",
        }

    def authorize(
        self,
        *,
        session_id: str,
        task_id: str,
        action: dict[str, Any],
    ) -> dict[str, Any]:
        kind = str(action.get("kind", ""))

        if kind == "filesystem.write":
            target = _resolved(str(action.get("path", "")))
            for root in self.canonical_roots:
                if _inside(target, root):
                    return self._decision(
                        session_id=session_id,
                        task_id=task_id,
                        action=action,
                        allowed=False,
                        reason=f"canonical repository write prohibited: {target}",
                        constraint="no canonical repository modifications",
                    )
            if not any(_inside(target, root) for root in self.writable_roots):
                return self._decision(
                    session_id=session_id,
                    task_id=task_id,
                    action=action,
                    allowed=False,
                    reason=f"write target is outside authorized roots: {target}",
                    constraint="writes restricted to declared disposable scope",
                )
            return self._decision(
                session_id=session_id,
                task_id=task_id,
                action=action,
                allowed=True,
                reason="write is within authorized disposable scope",
                constraint="writes restricted to declared disposable scope",
            )

        if kind == "process.run":
            argv = action.get("argv") or []
            if isinstance(argv, str):
                argv = shlex.split(argv)
            argv = [str(v) for v in argv]
            cwd = _resolved(str(action.get("cwd") or os.getcwd()))
            effective_argv = _resolve_command_argv(argv)
            base = _command_basename(effective_argv[0]) if effective_argv else ""
            lowered = [v.lower() for v in effective_argv]

            # Never execute commands from inside a protected repo in this vertical.
            if any(_inside(cwd, root) for root in self.canonical_roots):
                return self._decision(
                    session_id=session_id,
                    task_id=task_id,
                    action=action,
                    allowed=False,
                    reason=f"process working directory is a protected canonical repository: {cwd}",
                    constraint="no state-changing actions in canonical repositories",
                )

            git_subcommand = _git_subcommand(effective_argv) if base == "git" else None
            if self.prohibit_git_mutation and git_subcommand in _MUTATING_GIT:
                return self._decision(
                    session_id=session_id,
                    task_id=task_id,
                    action=action,
                    allowed=False,
                    reason=f"Git mutation prohibited: git {git_subcommand}",
                    constraint="no commit, push, branch, reset, clean, stash, or other Git mutation",
                )

            if self.prohibit_dependency_install and _install_requested(base, effective_argv):
                return self._decision(
                    session_id=session_id,
                    task_id=task_id,
                    action=action,
                    allowed=False,
                    reason="dependency installation prohibited",
                    constraint="no dependency installation",
                )

            nested_violation = _nested_shell_violation(base, effective_argv)
            if nested_violation:
                return self._decision(
                    session_id=session_id,
                    task_id=task_id,
                    action=action,
                    allowed=False,
                    reason=nested_violation,
                    constraint="prohibitions apply through nested shell commands",
                )

            if self.prohibit_deploy and (
                any(word in _DEPLOY_WORDS for word in lowered[1:])
                or (base in {"vercel", "wrangler", "render", "netlify", "firebase", "fly"} and len(lowered) > 1)
            ):
                return self._decision(
                    session_id=session_id,
                    task_id=task_id,
                    action=action,
                    allowed=False,
                    reason="deployment or publishing prohibited",
                    constraint="no deploy or publish",
                )

            if not any(_inside(cwd, root) or cwd == root for root in self.writable_roots):
                return self._decision(
                    session_id=session_id,
                    task_id=task_id,
                    action=action,
                    allowed=False,
                    reason=f"process cwd outside authorized disposable scope: {cwd}",
                    constraint="process execution restricted to declared disposable scope",
                )

            return self._decision(
                session_id=session_id,
                task_id=task_id,
                action=action,
                allowed=True,
                reason="process is read/verify work inside authorized disposable scope",
                constraint="process execution restricted to declared disposable scope",
            )

        return self._decision(
            session_id=session_id,
            task_id=task_id,
            action=action,
            allowed=False,
            reason=f"unknown operation kind: {kind or '<empty>'}",
            constraint="deny unknown operations",
        )


def guarded_write_text(
    path: str | os.PathLike[str],
    content: str,
    *,
    guard: PolicyGuard,
    session_id: str,
    task_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    target = _resolved(path)
    decision = guard.authorize(
        session_id=session_id,
        task_id=task_id,
        action={"kind": "filesystem.write", "path": str(target)},
    )
    if not decision["allowed"]:
        raise PolicyDenied(decision)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    decision["adapterInvocationStatus"] = "INVOKED"
    evidence = {
        "evidenceId": _id("write"),
        "timestamp": _now(),
        "sessionId": session_id,
        "taskId": task_id,
        "path": str(target),
        "bytes": len(content.encode("utf-8")),
        "sha256": _digest(content),
        "result": "written",
    }
    return decision, evidence


def guarded_run(
    argv: Sequence[str],
    *,
    cwd: str | os.PathLike[str],
    guard: PolicyGuard,
    session_id: str,
    task_id: str,
    timeout: int = 120,
) -> tuple[dict[str, Any], dict[str, Any]]:
    command = [str(v) for v in argv]
    workdir = _resolved(cwd)
    decision = guard.authorize(
        session_id=session_id,
        task_id=task_id,
        action={"kind": "process.run", "argv": command, "cwd": str(workdir)},
    )
    if not decision["allowed"]:
        raise PolicyDenied(decision)
    started = _now()
    proc = subprocess.run(
        command,
        cwd=str(workdir),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    ended = _now()
    decision["adapterInvocationStatus"] = "INVOKED"
    evidence = {
        "evidenceId": _id("command"),
        "sessionId": session_id,
        "taskId": task_id,
        "argv": command,
        "cwd": str(workdir),
        "startedAt": started,
        "endedAt": ended,
        "exitCode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "stdoutSha256": _digest(proc.stdout),
        "stderrSha256": _digest(proc.stderr),
    }
    return decision, evidence
