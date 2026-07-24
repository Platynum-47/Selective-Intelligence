# Platynum 👎 → SI interrupt wiring contract

Status: **contract + SI session-state backend shipped; product must call it**. Platynum live steering UI (PR #2) is **already merged**. Do not duplicate UI work. This document defines the backend contract SI exposes so the merged surface can become real session-state control.

## Problem

The merged UI can show “What I understand you want” and accept 👎. Without an authoritative SI interrupt transaction, dislike remains observation: generation, tool dispatch, and FS/Git mutations can continue under a rejected interpretation.

## Claim scope (honest)

SI `interrupt` is an **atomic SI session-state interruption**:

- Sets `generationAuthority=false`, `mutationFrozen=true`, `executionLocked=true`, `correctionMode=true`
- Marks queued tasks cancelled; marks running/verifying/repairing cancelled or cancellation-requested in session state
- Taints completed effects bound to the rejected checkpoint
- Emits a new proposed checkpoint; resume requires `approve`

Until a product connection proves that model generation streams, tool dispatchers, and external workers actually honor those flags and stop, do **not** claim a full hard-stop of those runtimes. Document product wiring as invoking the SI interrupt transaction; document remaining gaps as observational/external.

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
| `disliked_checkpoint_id` | recommended | Must equal `currentCheckpointId` or fail closed |
| `structured_intent` | optional | Validated override; never defeats text-derived RETRACT |

### Atomic effects (must all occur in one transaction)

1. Stop session generation authority for that checkpoint
2. Prevent new SI-gated tool dispatch
3. Cancel queued tasks bound to the checkpoint
4. Request cancel of running / verifying / repairing (not only pending) in session state
5. Freeze new FS / Git / deploy mutations gated by this session
6. Mark completed effects from the rejected checkpoint as potentially tainted
7. Capture the correction as an intent operation (`RETRACT`, etc.)
8. Create a new proposed checkpoint version
9. Return removed / retained / changed
10. Resume only after `approve` of the new checkpoint (which restores session `generationAuthority`)

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
5. Document honestly: wiring invokes SI session-state interrupt; external stop is proven only when product/runtime evidence shows model/tool/workers halt.

## Non-claims

- This contract being documented does **not** close the integrated Platynum↔SI loop until the product calls interrupt.
- Merged UI without wired interrupt is **not** Step-1 enforcement.
- Calling SI interrupt is **session-state control**, not automatic proof of external model/tool/worker stop.
- Cross-model reliability remains unproven until matrix evals pass across clients. Do not claim T2 from this wiring alone.
