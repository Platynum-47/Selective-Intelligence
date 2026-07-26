#!/usr/bin/env python3
"""Concept Rescue — two additional diverse cases beyond Steady Paws, SI-side proof.

Mirrors test_concept_rescue_vertical.py's checkpoint / interrupt / RETRACT / stale-
approval-fails-closed flow, parameterized across two artifact types genuinely
different from the original pilot (a consumer marketing/e-commerce site):

  Case 2: raw idea / pitch-deck-style artifact ("NovaDesk", synthetic SaaS pitch)
  Case 3: repository / technical artifact ("QueueForge", synthetic README)

Both user-facing artifact texts live in Platynum-47/src/conceptRescueCases.fixtures.ts
(diagnosis/detection is proven there). This file proves the SAME checkpoint/RETRACT/
fail-closed session-state machinery this lane already proved for Steady Paws also
holds for these two differently-worded, differently-domained intents — i.e. the SI
runtime authority is not accidentally keyed to Steady-Paws-specific wording either.

Local flow proof only — not production / cross-client / cross-model. See
Platynum-47/.selective-intelligence/concept-rescue-additional-cases-evidence.md for
the full honest write-up (evidence grades, decision gates, challenge review) and the
reasons the status ceiling does not move because of this file.
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


CASES = {
    "case2_novadesk_deck": {
        "ambiguous": "Create a better version of this deck.",
        "ambiguous_product_intent": "Create a better sales page for the referenced pitch deck",
        "correction": (
            "I do not own this. I am helping whoever is behind NovaDesk, and I also want "
            "to test Platynum's diagnosis workflow on a deck-style artifact. Do not build "
            "another sales page."
        ),
        "correction_product_intent": (
            "Help the original creator validate an unfinished pitch-deck artifact; "
            "prove Concept Rescue diagnosis on a deck-style input; do not build another "
            "sales page."
        ),
        "required_input": (
            "I found this NovaDesk pitch deck online while researching AI co-founder "
            "tools. I am not the founder — I want to help whoever is behind it think it "
            "through, and I also want Platynum to learn a reusable concept-rescue "
            "workflow from a deck-style artifact. I do not own this concept, brand, "
            "claims, or testimonials."
        ),
    },
    "case3_queueforge_repo": {
        "ambiguous": "Create a better version of this README.",
        "ambiguous_product_intent": "Create a better marketing README for the referenced repository",
        "correction": (
            "I do not own this repository. I am helping the maintainer see what's "
            "overclaimed, and I also want to test Platynum's diagnosis workflow on a "
            "technical/repo artifact. Do not build another sales page."
        ),
        "correction_product_intent": (
            "Help the original maintainer validate an unfinished repository README; "
            "prove Concept Rescue diagnosis on a technical/repo input; do not build "
            "another sales page."
        ),
        "required_input": (
            "I found this QueueForge repository README on GitHub. I don't maintain it "
            "— I want to help the maintainer see what's overclaimed before anyone "
            "relies on it, and I also want Platynum to learn how concept-rescue applies "
            "to a technical/repo artifact instead of a marketing page. I do not own "
            "this project or its claims."
        ),
    },
}


class ConceptRescueAdditionalCases(unittest.TestCase):
    def _run_ambiguous_then_correct(self, case_key: str) -> None:
        case = CASES[case_key]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            os.environ["SI_SESSION_DIR"] = str(root / "sessions")
            workspace = root / "ws"

            session = BE.start_project(
                request=case["ambiguous"],
                workspace=str(workspace),
                canonical_roots=[],
                plan={
                    "tasks": [
                        {
                            "key": "rebuild_asset",
                            "title": "Generate improved public asset scaffold",
                            "queue": "ready",
                            "kind": "worker",
                            "tags": ["build"],
                        }
                    ]
                },
                structured_intent={
                    "product_intent": case["ambiguous_product_intent"],
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
                "planId": f"{case_key}-mislabeled-stale-build",
                "tasks": [
                    {
                        "key": "mislabeled_rebuild",
                        "title": "Generate improved public asset scaffold",
                        "queue": "ready",
                        "kind": "analysis",
                        "tags": ["read-only"],
                    }
                ],
            }

            session, result = BE.interrupt_project(
                session_id=session["sessionId"],
                correction=case["correction"],
                disliked_checkpoint_id=stale_id,
                structured_intent={
                    "operation": "RETRACT",
                    "product_intent": case["correction_product_intent"],
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
            self.assertEqual(result["invalidatedPendingPlan"]["taskKeys"], ["rebuild_asset"])

            new_cp = result.get("newCheckpoint") or {}
            new_id = new_cp.get("checkpoint_id") or result.get("siCheckpointId")
            new_hash = new_cp.get("intent_hash") or result.get("newIntentHash")
            self.assertTrue(new_id)
            self.assertNotEqual(new_id, stale_id)
            self.assertEqual(new_cp.get("intent_summary"), case["correction_product_intent"])
            self.assertEqual(
                (session.get("activeIntent") or {}).get("product_intent"),
                case["correction_product_intent"],
            )

            # Stale checkpoint must fail closed even after RETRACT produced a new one.
            with self.assertRaises((CP.CheckpointError, BE.EngineError)):
                BE.approve_project(
                    session_id=session["sessionId"],
                    checkpoint_id=stale_id,
                    intent_hash=stale_hash,
                )

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
            self.assertEqual(intent.get("product_intent"), case["correction_product_intent"])
            self.assertEqual(approved.get("intent_summary"), case["correction_product_intent"])
            self.assertIn("do not build a sales page", prohibitions)
            self.assertIn("buildauthorized=false", constraints.replace(" ", ""))
            active_tasks = [
                task
                for task in session["queue"].values()
                if task.get("status") not in {"cancelled", "complete", "invalidated"}
            ]
            self.assertEqual(active_tasks, [])

            with self.assertRaises(BE.EngineError):
                BE.add_plan_tasks(session, stale_plan)
            with self.assertRaises(BE.EngineError):
                BE.add_plan_tasks(session, mislabeled_stale_plan)
            rogue = LS.add_task(
                session,
                title="Generate sales page scaffold",
                queue="ready",
                tags=["read-only"],
                metadata={"kind": "analysis", "planKey": "rogue_rebuild_asset"},
            )
            LS.save_session(session)
            with self.assertRaises(BE.EngineError) as dispatch_error:
                BE.make_worker_packet(session_id=session["sessionId"], task_id=rogue["taskId"])
            self.assertIn("active intent contract", str(dispatch_error.exception))

            # Status ceiling reference — the runtime does not claim past this.
            status = "Concept Rescue local flow-proven"
            self.assertNotIn("production proven", status)
            self.assertNotIn("cross-client", status)
            self.assertNotIn("cross-model", status)

    def test_case2_novadesk_deck_ambiguous_then_correct_retracts_and_blocks_stale_build_authority(self):
        self._run_ambiguous_then_correct("case2_novadesk_deck")

    def test_case3_queueforge_repo_ambiguous_then_correct_retracts_and_blocks_stale_build_authority(self):
        self._run_ambiguous_then_correct("case3_queueforge_repo")

    def _run_required_input_preserves_boundary(self, case_key: str) -> None:
        case = CASES[case_key]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            os.environ["SI_SESSION_DIR"] = str(root / "sessions")
            session = BE.start_project(
                request=case["required_input"],
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
                    "product_intent": case["required_input"],
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

    def test_case2_novadesk_deck_required_input_preserves_helper_ownership_boundary(self):
        self._run_required_input_preserves_boundary("case2_novadesk_deck")

    def test_case3_queueforge_repo_required_input_preserves_helper_ownership_boundary(self):
        self._run_required_input_preserves_boundary("case3_queueforge_repo")


if __name__ == "__main__":
    unittest.main()
