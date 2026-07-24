# Platynum 👎 → SI interrupt wiring contract

Status: **contract only**. Platynum live steering UI (PR #2) is **already merged**. Do not duplicate UI work. This document defines the backend contract SI exposes so the merged surface can become real control.

## Problem

The merged UI can show “What I understand you want” and accept 👎. Without an authoritative SI interrupt transaction, dislike remains observation: generation, tool dispatch, and FS/Git mutations can continue under a rejected interpretation.

## SI endpoint (authoritative)

```
POST /si/v1/sessions/{session_id}/interrupt
```

CLI equivalent (shipped in SI runtime):

```
python build_engine.py interrupt \
  --session <session_id> \
  --correction "<user correction text>" \
  [--checkpoint <disliked_checkpoint_id>]
```

Also available as `correct` (stores optional pending plan; still requires `approve`).

### Request

| Field | Required | Meaning |
| --- | --- | --- |
| `correction` | yes | Raw user text (e.g. “i didnt say halt did i? nope.”) |
| `disliked_checkpoint_id` | recommended | Checkpoint the user disliked |
| `structured_intent` | optional | Validated override; never the only path to RETRACT correctness |

### Atomic effects (must all occur in one transaction)

1. Stop generation authority for that checkpoint
2. Prevent new tool dispatch
3. Cancel queued tasks bound to the checkpoint
4. Request cancel of running / verifying / repairing (not only pending)
5. Freeze new FS / Git / deploy mutations
6. Mark completed effects from the rejected checkpoint as potentially tainted
7. Capture the correction as an intent operation (`RETRACT`, etc.)
8. Create a new proposed checkpoint version
9. Return removed / retained / changed
10. Resume only after `approve` of the new checkpoint

### Response (minimum)

```json
{
  "interruptedCheckpointId": "cp-…",
  "newCheckpoint": { "checkpoint_id": "cp-…", "status": "proposed", "intent_hash": "…" },
  "operation": "RETRACT",
  "cancelledTaskIds": [],
  "cancelRequestedTaskIds": [],
  "taintedEffectIds": [],
  "removed": {},
  "retained": {},
  "changed": {},
  "resumeRequiresApproval": true,
  "mutationFrozen": true,
  "generationAuthority": false
}
```

## Platynum client obligations

On 👎 (or equivalent hard interrupt):

1. Call SI `interrupt` **before** allowing any further mutating tool calls.
2. Bind subsequent work only to `newCheckpoint.checkpoint_id` after user Continu/Approve maps to SI `approve`.
3. Do not invent halt-all / restart-project / new-branch policies from the dislike itself.
4. Treat SI as interpretation authority; model text is proposal only.

## Non-claims

- This contract being documented does **not** close the integrated Platynum↔SI loop.
- Merged UI without wired interrupt is **not** Step-1 enforcement.
- Cross-model reliability remains unproven until matrix evals pass across clients.
