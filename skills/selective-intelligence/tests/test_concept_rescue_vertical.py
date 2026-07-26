#!/usr/bin/env python3
"""Concept Rescue vertical — SI checkpoint / interrupt / RETRACT proof.

Uses existing build_engine + checkpoint paths. Does not commercialize third-party
brands. Local flow proof only — not production / cross-client / cross-model.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SKILL_ROOT = TEST_DIR.parent
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_engine as BE
import checkpoint as CP
import lane_session as LS


REQUIRED_INPUT = (
    "I found this Steady Paws proof of concept online. I am trying to help the creator "
    "improve or validate it. I also want Platynum to learn a reusable concept-rescue "
    "workflow from the case. I do not own the original concept, brand, claims, "
    "testimonials, or assets."
)

AMBIGUOUS = "Create a better version."

CORRECTION = (
    "I do not own this. I am helping the creator, and I also want to test Platynum’s "
    "diagnosis workflow. Do not build another sales page."
)

CORRECTED_PRODUCT_INTENT = (
    "Help the original creator validate an unfinished proof of concept; "
    "prove Concept Rescue diagnosis; do not build another sales page."
)


class ConceptRescueVertical(unittest.TestCase):
    def test_ambiguous_then_correct_retracts_and_blocks_stale_build_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            os.environ["SI_SESSION_DIR"] = str(root / "sessions")
            workspace = root / "ws"

            session = BE.start_project(
                request=AMBIGUOUS,
                workspace=str(workspace),
                canonical_roots=[],
                plan={
                    "tasks": [
                        {
                            "key": "sales_page",
                            "title": "Generate sales page scaffold",
                            "queue": "ready",
                            "kind": "worker",
                            "tags": ["build", "landing-page"],
                        }
                    ]
                },
                structured_intent={
                    "product_intent": "Create a better sales page for the referenced concept",
                    "constraints": [],
                    "prohibitions": [],
                },
                auto_approve=False,
            )
            self.assertFalse(session.get("generationAuthority"))
            proposed = CP.current_checkpoint(session)
            self.assertIsNotNone(proposed)
            self.assertEqual(proposed["status"], "proposed")
            stale_id = proposed["checkpoint_id"]
            stale_hash = proposed["intent_hash"]
            stale_plan = session["pendingPlan"]
            mislabeled_stale_plan = {
                "planId": "mislabeled-stale-sales-page",
                "tasks": [
                    {
                        "key": "mislabeled_sales_page",
                        "title": "Generate sales page scaffold",
                        "queue": "ready",
                        "kind": "analysis",
                        "tags": ["read-only"],
                    }
                ],
            }
            euphemistic_stale_plan = {
                "planId": "mislabeled-euphemistic-build",
                "tasks": [
                    {
                        "key": "launch_experience",
                        "title": "Launch improved sales experience",
                        "queue": "ready",
                        "kind": "analysis",
                        "tags": ["read-only"],
                    }
                ],
            }

            session, result = BE.interrupt_project(
                session_id=session["sessionId"],
                correction=CORRECTION,
                disliked_checkpoint_id=stale_id,
                structured_intent={
                    "operation": "RETRACT",
                    "product_intent": CORRECTED_PRODUCT_INTENT,
                    "prohibitions": [
                        "do not build a sales page",
                        "do not commercialize third-party branding",
                    ],
                    "constraints": [
                        "artifactOwnership=third_party",
                        "userRelationship=helper_or_advisor",
                        "secondaryIntent=derive_generalized_workflow",
                        "buildAuthorized=false",
                        "commercialReuseAuthorized=false",
                        "artifactStage=unfinished_proof_of_concept",
                    ],
                },
            )
            self.assertEqual(result.get("operation"), "RETRACT")
            self.assertFalse(session.get("generationAuthority"))
            self.assertNotIn("pendingPlan", session)
            self.assertEqual(result["invalidatedPendingPlan"]["taskKeys"], ["sales_page"])

            new_cp = result.get("newCheckpoint") or {}
            new_id = new_cp.get("checkpoint_id") or result.get("siCheckpointId")
            new_hash = new_cp.get("intent_hash") or result.get("newIntentHash")
            self.assertTrue(new_id)
            self.assertNotEqual(new_id, stale_id)
            self.assertEqual(new_cp.get("intent_summary"), CORRECTED_PRODUCT_INTENT)
            self.assertEqual(
                (session.get("activeIntent") or {}).get("product_intent"),
                CORRECTED_PRODUCT_INTENT,
            )

            with self.assertRaises((CP.CheckpointError, BE.EngineError)):
                BE.approve_project(
                    session_id=session["sessionId"],
                    checkpoint_id=stale_id,
                    intent_hash=stale_hash,
                )

            # A pre-correction plan cannot be resubmitted as if it were corrected.
            with self.assertRaises(BE.EngineError):
                BE.approve_project(
                    session_id=session["sessionId"],
                    checkpoint_id=new_id,
                    intent_hash=new_hash,
                    plan=mislabeled_stale_plan,
                )

            session = BE.approve_project(
                session_id=session["sessionId"],
                checkpoint_id=new_id,
                intent_hash=new_hash,
            )
            approved = CP.get_checkpoint(session, new_id)
            self.assertEqual(approved["status"], "approved")
            self.assertTrue(session.get("generationAuthority"))

            intent = session.get("activeIntent") or {}
            prohibitions = " ".join(intent.get("prohibitions") or []).lower()
            constraints = " ".join(intent.get("constraints") or []).lower()
            summary = (approved.get("intent_summary") or intent.get("product_intent") or "").lower()
            self.assertEqual(intent.get("product_intent"), CORRECTED_PRODUCT_INTENT)
            self.assertEqual(approved.get("intent_summary"), CORRECTED_PRODUCT_INTENT)
            self.assertIn("do not build a sales page", prohibitions)
            self.assertIn("buildauthorized=false", constraints.replace(" ", ""))
            active_tasks = [
                task
                for task in session["queue"].values()
                if task.get("status") not in {"cancelled", "complete", "invalidated"}
            ]
            self.assertEqual(active_tasks, [])

            # Plan application and the final dispatch boundary both fail closed.
            with self.assertRaises(BE.EngineError):
                BE.add_plan_tasks(session, stale_plan)
            with self.assertRaises(BE.EngineError):
                BE.add_plan_tasks(session, mislabeled_stale_plan)
            with self.assertRaises(BE.EngineError) as euphemistic_plan_error:
                BE.add_plan_tasks(session, euphemistic_stale_plan)
            self.assertIn("buildAuthorized=false", str(euphemistic_plan_error.exception))
            rogue = LS.add_task(
                session,
                title="Generate sales page scaffold",
                queue="ready",
                tags=["read-only"],
                metadata={"kind": "analysis", "planKey": "rogue_sales_page"},
            )
            LS.save_session(session)
            with self.assertRaises(BE.EngineError) as dispatch_error:
                BE.make_worker_packet(session_id=session["sessionId"], task_id=rogue["taskId"])
            self.assertIn("active intent contract", str(dispatch_error.exception))
            euphemistic_rogue = LS.add_task(
                session,
                title="Launch improved sales experience",
                queue="ready",
                tags=["read-only"],
                metadata={"kind": "analysis", "planKey": "rogue_launch_experience"},
            )
            LS.save_session(session)
            with self.assertRaises(BE.EngineError) as euphemistic_dispatch_error:
                BE.make_worker_packet(
                    session_id=session["sessionId"],
                    task_id=euphemistic_rogue["taskId"],
                )
            self.assertIn("buildAuthorized=false", str(euphemistic_dispatch_error.exception))

            # Read-only diagnosis may be dispatched, but its label cannot
            # authorize a filesystem mutation while build remains prohibited.
            analysis_task = LS.add_task(
                session,
                title="Review diagnostic evidence",
                queue="ready",
                tags=["read-only"],
                metadata={"kind": "analysis", "planKey": "diagnostic_review"},
            )
            LS.save_session(session)
            packet = BE.make_worker_packet(
                session_id=session["sessionId"],
                task_id=analysis_task["taskId"],
            )
            self.assertEqual(packet["taskId"], analysis_task["taskId"])
            with self.assertRaises(BE.EngineError) as mutation_error:
                BE.apply_worker_artifact(
                    session_id=session["sessionId"],
                    task_id=analysis_task["taskId"],
                    artifact={
                        "files": {"analysis.txt": "diagnostic evidence\n"},
                        "producer": {
                            "adapterId": "test-adapter",
                            "surface": "unit-test",
                            "generatedAt": "2026-07-25T00:00:00+00:00",
                        },
                    },
                )
            self.assertIn("buildAuthorized=false", str(mutation_error.exception))
            self.assertFalse((workspace / "analysis.txt").exists())

            status = "Concept Rescue local flow-proven"
            self.assertNotIn("production proven", status)
            self.assertNotIn("cross-client", status)
            self.assertNotIn("cross-model", status)

    def test_required_input_preserves_helper_ownership_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            os.environ["SI_SESSION_DIR"] = str(root / "sessions")
            session = BE.start_project(
                request=REQUIRED_INPUT,
                workspace=str(root / "ws2"),
                canonical_roots=[],
                plan={
                    "tasks": [
                        {
                            "key": "analysis_only",
                            "title": "Review ownership boundaries and validation evidence",
                            "queue": "ready",
                            "kind": "analysis",
                        }
                    ]
                },
                structured_intent={
                    "product_intent": REQUIRED_INPUT,
                    "constraints": [
                        "artifactOwnership=third_party",
                        "userRelationship=helper_or_advisor",
                        "buildAuthorized=false",
                        "commercialReuseAuthorized=false",
                    ],
                    "prohibitions": [
                        "do not treat the artifact as user-owned",
                        "do not generate commercial funnel assets",
                    ],
                },
                auto_approve=False,
            )
            cp = CP.current_checkpoint(session)
            self.assertEqual(cp["status"], "proposed")
            self.assertFalse(session.get("generationAuthority"))
            blob = " ".join(cp.get("constraints") or []).lower()
            self.assertIn("third_party", blob.replace("-", "_"))
            self.assertIn("buildauthorized=false", blob.replace(" ", ""))


if __name__ == "__main__":
    unittest.main()
