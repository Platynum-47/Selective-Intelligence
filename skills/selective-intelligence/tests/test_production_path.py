from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SKILL_ROOT = TEST_DIR.parent
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import capabilities as CAP
import intent_contract as IC
import lane_session as LS
import build_engine as BE
from policy_guard import PolicyGuard


class IntentContractTests(unittest.TestCase):
    def test_explicit_prohibitions_survive_classification(self):
        event = IC.classify_intent(
            "Build a page. Do not commit, push, or install dependencies. The page must show verified adapters only."
        )
        self.assertTrue(any("Do not" in value for value in event["prohibitions"]))
        self.assertTrue(any("verified" in value.lower() for value in event["acceptance_criteria"]))


class CapabilityTests(unittest.TestCase):
    def test_only_probe_verified_capabilities_are_executable(self):
        with tempfile.TemporaryDirectory() as temp:
            reports = CAP.inventory(probe_root=temp)
        python = next(report for report in reports if report["adapterId"] == "python3_runtime")
        self.assertTrue(python["discovered"])
        self.assertTrue(python["adapterImplemented"])
        self.assertEqual(python["probeStatus"], "verified")
        self.assertTrue(python["executable"])
        credential = next(report for report in reports if report["adapterId"] == "anthropic_credential_reference")
        self.assertFalse(credential["executable"])
        self.assertEqual(credential["verifiedCapabilities"], [])


class SessionTests(unittest.TestCase):
    def test_correction_invalidates_only_affected_pending_work(self):
        with tempfile.TemporaryDirectory() as temp:
            os.environ["SI_SESSION_DIR"] = temp
            session = LS.new_session("Build a generic status panel")
            discovery = LS.add_task(session, title="discover", queue="discovery", tags=["discovery"])
            LS.transition_task(session, discovery["taskId"], "running")
            LS.transition_task(session, discovery["taskId"], "verifying")
            LS.transition_task(session, discovery["taskId"], "complete")
            generic = LS.add_task(
                session,
                title="generic health",
                queue="ready",
                dependencies=[discovery["taskId"]],
                tags=["generic_health"],
                invalidation_conditions=["generic service health"],
            )
            result = LS.add_correction(
                session,
                "Display only verified adapter capabilities, not generic service health.",
            )
            self.assertIn(generic["taskId"], result["invalidatedTaskIds"])
            self.assertIn(discovery["taskId"], result["preservedCompletedTaskIds"])


class WorkerPacketTests(unittest.TestCase):
    def test_packet_preserves_constraints_and_excludes_sensitive_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace = root / "workspace"
            session_dir = root / "sessions"
            workspace.mkdir()
            (workspace / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
            (workspace / ".env").write_text("API_KEY=should-not-export\n", encoding="utf-8")
            os.environ["SI_SESSION_DIR"] = str(session_dir)
            plan = {
                "tasks": [
                    {"key": "discovery", "title": "discover", "queue": "discovery", "kind": "discovery"},
                    {"key": "work", "title": "work", "queue": "ready", "kind": "worker", "dependencies": ["discovery"]},
                ]
            }
            session = BE.start_project(
                request="Change app.py. Do not commit or expose secrets.",
                workspace=str(workspace),
                canonical_roots=[],
                plan=plan,
            )
            task = next(t for t in session["queue"].values() if t["metadata"].get("planKey") == "work")
            packet = BE.make_worker_packet(session_id=session["sessionId"], task_id=task["taskId"])
            selected = {item["path"] for item in packet["contextBundle"]["selected"]}
            excluded = {item["path"] for item in packet["contextBundle"]["excluded"]}
            self.assertIn("app.py", selected)
            self.assertIn(".env", excluded)
            self.assertTrue(packet["activeIntent"]["prohibitions"])
            self.assertNotIn("API_KEY=should-not-export", json.dumps(packet))


class PolicyTests(unittest.TestCase):
    def test_denies_before_adapter_invocation(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            canonical = base / "canonical"
            disposable = base / "disposable"
            canonical.mkdir()
            disposable.mkdir()
            guard = PolicyGuard(canonical_roots=[canonical], writable_roots=[disposable])
            decision = guard.authorize(
                session_id="si-test",
                task_id="task-test",
                action={"kind": "filesystem.write", "path": str(canonical / "bad.txt")},
            )
            self.assertFalse(decision["allowed"])
            self.assertEqual(decision["adapterInvocationStatus"], "NOT_INVOKED")
            self.assertFalse((canonical / "bad.txt").exists())

            bypasses = [
                ["git", "-C", str(disposable), "commit", "-m", "bad"],
                ["bash", "-c", "git commit -m bad"],
                ["npm", "--prefix", str(disposable), "install", "bad-package"],
            ]
            for argv in bypasses:
                nested = guard.authorize(
                    session_id="si-test",
                    task_id="task-test",
                    action={"kind": "process.run", "argv": argv, "cwd": str(disposable)},
                )
                self.assertFalse(nested["allowed"], argv)
                self.assertEqual(nested["adapterInvocationStatus"], "NOT_INVOKED")


class FullVerticalTests(unittest.TestCase):
    def test_vertical(self):
        runner = TEST_DIR / "run_instruction_fidelity_vertical.py"
        with tempfile.TemporaryDirectory() as temp:
            evidence_out = Path(temp) / "evidence.json"
            env = os.environ.copy()
            env["SI_VERTICAL_EVIDENCE_OUT"] = str(evidence_out)
            proc = subprocess.run(
                [sys.executable, str(runner)],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
            result = json.loads(proc.stdout)
            self.assertEqual(result["classification"], "PRODUCTION_MODULE_PATH_PASS")
            self.assertEqual(result["failedExitCode"], 1)
            self.assertEqual(result["passedExitCode"], 0)
            self.assertEqual(result["deniedActionCount"], 4)
            self.assertTrue(result["canonicalUnchanged"])
            self.assertEqual(result["finalState"], "VERIFIED_COMPLETE")
            self.assertTrue(evidence_out.exists())


if __name__ == "__main__":
    unittest.main()
