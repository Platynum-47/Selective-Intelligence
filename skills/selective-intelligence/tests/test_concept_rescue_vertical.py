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

            session, result = BE.interrupt_project(
                session_id=session["sessionId"],
                correction=CORRECTION,
                disliked_checkpoint_id=stale_id,
                structured_intent={
                    "operation": "RETRACT",
                    "product_intent": (
                        "Help the original creator validate an unfinished proof of concept; "
                        "prove Concept Rescue diagnosis; do not build another sales page."
                    ),
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

            new_cp = result.get("newCheckpoint") or {}
            new_id = new_cp.get("checkpoint_id") or result.get("siCheckpointId")
            new_hash = new_cp.get("intent_hash") or result.get("newIntentHash")
            self.assertTrue(new_id)
            self.assertNotEqual(new_id, stale_id)

            with self.assertRaises((CP.CheckpointError, BE.EngineError)):
                BE.approve_project(
                    session_id=session["sessionId"],
                    checkpoint_id=stale_id,
                    intent_hash=stale_hash,
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
            blob = f"{prohibitions} {constraints} {summary}"
            self.assertTrue("sales page" in blob or "third_party" in blob.replace("-", "_"))

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
                            "title": "Hold analysis only — no commercial build",
                            "queue": "ready",
                            "kind": "worker",
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
