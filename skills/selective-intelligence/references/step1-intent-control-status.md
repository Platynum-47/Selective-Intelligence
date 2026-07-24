# Step-1 intent-control runtime status

Governing diagnosis (authoritative): SI doctrine was ahead of runtime. “Documented is not enforced” described SI itself. Failure occurs **before** PolicyGuard / tests / verification matter when the model acts on an unapproved interpretation.

**Root cause:** SI did not own interpretation authority.

**Required sequence:** reject-before-wrong-work (not post-hoc feedback metrics).

**TradeScout profile seeding** worked because a golden pre-specified packet already did Step-1. Ordinary live conversation did not get equivalent enforcement. PolicyGuard pass ≠ Step-1 fidelity.

## Platynum surface vs SI authority

| Layer | Status |
| --- | --- |
| Platynum T0 | Shipped |
| Platynum live steering UI / gate (PR #2) | **Merged** — user-visible “What I understand you want” + 👎 surface |
| Platynum T2 Intelligence/Checkpoint product loop | Pending |
| SI Step-1 P0 (ops 1–4) | **Enforced in Python runtime** (this release) |
| Platynum 👎 → SI `interrupt` product wiring | **Contract documented; product wiring still open** |
| Cross-model / cross-client equivalence | **Unproven** — do not claim REVIEW_PASS or Tier-4 |

Merged Platynum PR #2 is a shipped **surface**. Without SI interrupt + checkpoint binding it is observation, not control. Do not re-open or duplicate that UI work in SI.

## Screenshot failure class (acceptance)

User narrow instruction → agent invents halt → user: “i didnt say halt did i? nope.” → agent invents freeze/resume → user corrects → agent narrates unrelated background work.

That is Step-1 intent-control failure. Keyword parsers that miss `didnt`≠`don't`, `nope`≠standalone `no`, and treat `halt` as product intent fall through incorrectly.

**Now enforced (deterministic):** that utterance classifies as `RETRACT` of the halt interpretation, not product intent; interrupt cancels queued work, requests cancel of running/verifying/repairing, taints rejected-checkpoint effects, and requires a new approved checkpoint before resume.

## Enforced now (P0 ops 1–4)

1. **Intent operations** — `ADD | MODIFY | REPLACE | RETRACT | SUPERSEDE | ROLLBACK` in `scripts/intent_contract.py`. Repudiations are not unioned into refinements.
2. **First checkpoint = execution lock** — `start` emits a **proposed** checkpoint; plan/discovery/worker/FS/Git/external work stays locked until `approve`.
3. **Bind all work** — tasks, worker packets, artifacts, verifications, and action receipts carry `authorized_checkpoint_id` + `authorized_intent_hash`. Stale hash / unapproved / superseded / correction-mode → fail closed.
4. **Atomic interrupt** — `build_engine interrupt|correct` and `checkpoint.interrupt`: stop generation authority, prevent tool dispatch, cancel queued tasks, cancel/request-cancel running+verifying+repairing, freeze mutations, taint completed effects from the rejected checkpoint, capture correction, emit new proposed checkpoint, show removed/retained/changed, resume only after approve.

## Still doctrine / scaffolded (ops 5–7)

5. **Semantic corrections** — deterministic retract/replace paths exist; richer conversational ops (“criticism not new task”, “preserve objective, remove process directive”) are scaffolded in evals as `pending_semantic` and must not be claimed complete.
6. **Platynum wiring contract** — see [platynum-interrupt-wiring.md](platynum-interrupt-wiring.md). UI alone is insufficient.
7. **Behavioral matrix / cross-client evals** — cases added; pass requires equivalent authoritative intent **and** equivalent outcome across clients. Not claimed here.

## Honest taxonomy

- **Platynum surface:** T0 + merged live-steering UI (PR #2)
- **Intelligence/checkpoint product:** pre-T2
- **SI:** partial Tier-1 controls; **Step-1 P0 ops 1–4 qualified in SI runtime tests**; integrated Platynum↔SI loop **not closed**; cross-model equivalence **unproven**
