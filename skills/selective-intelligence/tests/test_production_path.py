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
import checkpoint as CP
import intent_contract as IC
import lane_session as LS
import build_engine as BE
from policy_guard import PolicyGuard


def _approve_current(session: dict) -> dict:
    checkpoint = CP.current_checkpoint(session)
    assert checkpoint is not None
    return CP.approve_checkpoint(session, checkpoint["checkpoint_id"])


class IntentContractTests(unittest.TestCase):
    def test_explicit_prohibitions_survive_classification(self):
        event = IC.classify_intent(
            "Build a page. Do not commit, push, or install dependencies. The page must show verified adapters only."
        )
        self.assertTrue(any("Do not" in value for value in event["prohibitions"]))
        self.assertTrue(any("verified" in value.lower() for value in event["acceptance_criteria"]))
        self.assertEqual(event["operation"], "ADD")

    def test_screenshot_failure_didnt_say_halt_is_retract(self):
        """Acceptance: 'i didnt say halt did i? nope.' → RETRACT, not product intent."""
        event = IC.classify_intent(
            "i didnt say halt did i? nope.",
            event_type="correction",
        )
        self.assertEqual(event["operation"], "RETRACT")
        self.assertTrue(any("halt" in t.lower() for t in event["operation_targets"]))
        self.assertEqual(event["product_intent"], "")
        # Must not fall through as a product ask.
        self.assertFalse(event["process_directives"])

    def test_retract_does_not_union_into_refinements(self):
        base = IC.classify_intent("Build the status panel and keep working.")
        active = IC.merge_active_contract(None, base)
        # Simulate a bad prior interpretation that invented halt.
        active["process_directives"] = ["halt all work until freeze/resume"]
        active["intent_hash"] = IC.intent_hash(active)
        correction = IC.classify_intent("i didnt say halt did i? nope.", event_type="correction")
        merged = IC.merge_active_contract(active, correction)
        self.assertEqual(correction["operation"], "RETRACT")
        self.assertEqual(merged.get("lastOperation"), "RETRACT")
        self.assertFalse(any("halt" in d.lower() for d in merged.get("process_directives", [])))
        refinements = merged.get("refinements") or []
        self.assertFalse(any("halt" in r.lower() or "nope" in r.lower() for r in refinements))
        self.assertTrue(merged.get("retractedInterpretations"))


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


class CheckpointLockTests(unittest.TestCase):
    def test_no_side_effecting_work_before_approved_checkpoint(self):
        with tempfile.TemporaryDirectory() as temp:
            os.environ["SI_SESSION_DIR"] = temp
            session = BE.start_project(
                request="Build a status panel",
                workspace=str(Path(temp) / "ws"),
                canonical_roots=[],
                plan={
                    "tasks": [
                        {"key": "discovery", "title": "discover", "queue": "discovery", "kind": "discovery"},
                        {"key": "work", "title": "work", "queue": "ready", "kind": "worker", "dependencies": ["discovery"]},
                    ]
                },
                auto_approve=False,
            )
            self.assertTrue(session["executionLocked"])
            self.assertTrue(session["mutationFrozen"])
            self.assertEqual(session["queue"], {})
            self.assertIsNotNone(session.get("pendingPlan"))
            current = CP.current_checkpoint(session)
            self.assertEqual(current["status"], "proposed")
            with self.assertRaises(BE.EngineError):
                BE.add_plan_tasks(session, session["pendingPlan"])
            with self.assertRaises(CP.CheckpointError):
                LS.add_task(session, title="sneaky", queue="ready")

    def test_approve_unlocks_plan_and_binds_checkpoint(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            os.environ["SI_SESSION_DIR"] = str(root / "sessions")
            workspace = root / "ws"
            session = BE.start_project(
                request="Build a status panel",
                workspace=str(workspace),
                canonical_roots=[],
                plan={
                    "tasks": [
                        {"key": "discovery", "title": "discover", "queue": "discovery", "kind": "discovery"},
                        {"key": "work", "title": "work", "queue": "ready", "kind": "worker", "dependencies": ["discovery"]},
                    ]
                },
            )
            session = BE.approve_project(session_id=session["sessionId"])
            self.assertFalse(session["executionLocked"])
            self.assertTrue(session["authorizedCheckpointId"])
            self.assertTrue(session["queue"])
            for task in session["queue"].values():
                self.assertEqual(task["authorized_checkpoint_id"], session["authorizedCheckpointId"])
                self.assertEqual(task["authorized_intent_hash"], session["authorizedIntentHash"])


class InterruptTests(unittest.TestCase):
    def test_interrupt_cancels_queued_and_running_and_taints_completed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            os.environ["SI_SESSION_DIR"] = str(root / "sessions")
            session = BE.start_project(
                request="Build a generic status panel",
                workspace=str(root / "ws"),
                canonical_roots=[],
                plan={
                    "tasks": [
                        {"key": "discovery", "title": "discover", "queue": "discovery", "kind": "discovery"},
                        {
                            "key": "work",
                            "title": "generic health",
                            "queue": "ready",
                            "kind": "worker",
                            "dependencies": ["discovery"],
                            "tags": ["generic_health"],
                        },
                    ]
                },
                auto_approve=True,
            )
            discovery = next(t for t in session["queue"].values() if t["metadata"]["planKey"] == "discovery")
            work = next(t for t in session["queue"].values() if t["metadata"]["planKey"] == "work")
            self.assertEqual(discovery["status"], "complete")
            # Put worker into running to prove interrupt does not skip in-flight statuses.
            ok, reason = LS.transition_task(session, work["taskId"], "running")
            self.assertTrue(ok, reason)
            LS.save_session(session)

            session, result = BE.interrupt_project(
                session_id=session["sessionId"],
                correction="i didnt say halt did i? nope.",
            )
            self.assertEqual(result["operation"], "RETRACT")
            self.assertTrue(session["mutationFrozen"])
            self.assertTrue(session["executionLocked"])
            self.assertTrue(session["correctionMode"])
            self.assertIn(work["taskId"], result["cancelledTaskIds"])
            self.assertTrue(any(session["queue"][tid].get("tainted") for tid in result["taintedEffectIds"] if tid in session["queue"]))
            # No new side effects until re-approve.
            with self.assertRaises(BE.EngineError):
                BE.make_worker_packet(session_id=session["sessionId"], task_id=work["taskId"])

    def test_stale_checkpoint_hash_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            os.environ["SI_SESSION_DIR"] = str(root / "sessions")
            session = BE.start_project(
                request="Build a panel",
                workspace=str(root / "ws"),
                canonical_roots=[],
                plan={
                    "tasks": [
                        {"key": "discovery", "title": "discover", "queue": "discovery", "kind": "discovery"},
                        {"key": "work", "title": "work", "queue": "ready", "kind": "worker", "dependencies": ["discovery"]},
                    ]
                },
                auto_approve=True,
            )
            work = next(t for t in session["queue"].values() if t["metadata"]["planKey"] == "work")
            work["authorized_intent_hash"] = "deadbeef" * 8
            LS.save_session(session)
            with self.assertRaises(BE.EngineError):
                BE.make_worker_packet(session_id=session["sessionId"], task_id=work["taskId"])


class SessionTests(unittest.TestCase):
    def test_correction_interrupts_and_taints_instead_of_preserving_completed(self):
        with tempfile.TemporaryDirectory() as temp:
            os.environ["SI_SESSION_DIR"] = temp
            session = LS.new_session("Build a generic status panel")
            _approve_current(session)
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
            # Move generic into verifying to prove we no longer skip that status.
            LS.transition_task(session, generic["taskId"], "running")
            LS.transition_task(session, generic["taskId"], "verifying")
            result = LS.add_correction(
                session,
                "Display only verified adapter capabilities, not generic service health.",
            )
            self.assertIn(generic["taskId"], result["cancelledTaskIds"])
            self.assertEqual(result["preservedCompletedTaskIds"], [])
            self.assertIn(discovery["taskId"], result["taintedEffectIds"])
            self.assertTrue(session["queue"][discovery["taskId"]].get("tainted"))
            self.assertTrue(session["mutationFrozen"])


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
                auto_approve=True,
            )
            task = next(t for t in session["queue"].values() if t["metadata"].get("planKey") == "work")
            packet = BE.make_worker_packet(session_id=session["sessionId"], task_id=task["taskId"])
            selected = {item["path"] for item in packet["contextBundle"]["selected"]}
            excluded = {item["path"] for item in packet["contextBundle"]["excluded"]}
            self.assertIn("app.py", selected)
            self.assertIn(".env", excluded)
            self.assertTrue(packet["activeIntent"]["prohibitions"])
            self.assertEqual(packet["authorized_checkpoint_id"], session["authorizedCheckpointId"])
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
