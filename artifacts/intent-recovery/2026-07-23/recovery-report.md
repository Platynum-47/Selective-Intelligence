# Intent Recovery & Queue Reconciliation — Recovery Report

**Run:** 2026-07-23 · **Owner:** Thomas · **Scope:** Selective-Intelligence + Platynum-47
**Status:** read-only forensic audit. **No runtime feature implementation occurred in this pass.**

## 1. What this is
The current repos are treated as **forensic evidence of a failed SI dogfood run**, not as the
product north star. This audit recovers the authoritative intent, the facts SI should have
gathered, the contradictions it ignored, and the queue drift — and defines the *real* first
executable. Implementation is **frozen** until the north star and first executable are explicit
and accepted by Thomas.

## 2. Verified baselines (read-only)
- **SI:** `Platynum-Standard/Selective-Intelligence` · branch `feat/friction-ladder` · HEAD `bd5d097` · clean.
- **Platynum-47:** `infotradescout/platynum-47` · branch `feat/t2-checkpoint` · HEAD `018f9cd` · clean.
  Other branches: `feat/mvp-editor`, `feat/t1-github-connector`, `feat/t1-oauth-broker`.
- No stray worktrees; nothing modified, reset, cleaned, or staged during the audit.

## 3. What failed (root cause)
Not primarily an execution-engine bug — a failure at **intent intake, fact gathering, queue
control, and drift detection**:
1. **Code treated as the objective.** The authority order (explicit intent → facts → acceptance →
   architecture → code) was inverted into (current code → latest prompt → local architecture change
   → more code). That is drift.
2. **Implemented before an intent contract existed.** No known/unknown/contradiction/assumption
   model preceded work.
3. **Machine-discoverable facts not exhausted** before restructuring, assuming keys, or adding
   infrastructure.
4. **New intent not reconciled.** Each correction became another architecture slice instead of
   triggering reconciliation + impact analysis + invalidation. *(I repeated exactly the failure
   Thomas named.)*
5. **Queue used as project truth** rather than a derived execution state under authoritative
   ledgers.
6. **Infrastructure optimized before the first executable was proven.** Lane registry, session,
   capabilities resolver — all downstream choices — were built around an unverified interpretation
   of SI's core promise.

## 4. Deliverables in this directory
- `intent-ledger.jsonl` — 25 material intents/corrections (I001–I025), faithful, authority-ordered.
- `fact-ledger.jsonl` — 14 facts (repo state, capabilities, gaps), discovery actions noted.
- `contradiction-report.json` — 7 contradictions (C1–C7) with resolutions.
- `north-star-contract.json` — provisional; `openForThomas` lists what still needs his decision.
- `first-executable-acceptance.json` — the real first-executable (a vertical slice, **not** "a lane
  registry exists").
- `current-state-gap-map.json` — component-by-component gaps + dispositions.
- `code-classification.json` — KEEP / ADAPT / QUARANTINE / REMOVE (no sunk-cost protection).
- `queue-reconciliation.json` — authoritative ledgers → derived queues; reconciled queue now.
- `drift-regression-cases.json` — D1–D12; the actual failures as fail-closed checks.

## 5. Headline findings
- **Capability-first is real and correct.** On this machine, with *zero keys*, SI already sees
  `gh, git, node, npm, python, shell, human`. Model-lanes are blocked only because no reasoning
  adapter is installed — *not* "globally unconfigured" (fact F005/F006).
- **Session split-brain is fixed** (0d10cd2) and belongs as a passing regression (D6/D8).
- **No product acceptance has ever run** (F010). Everything shipped is infrastructure.
- **The lane kernel is a hypothesis** (C3), not proof of the correct first implementation.

## 6. Smallest valid vertical plan (proposed, NOT started)
1. **Accept the north star + first-executable target** (Thomas) — resolve `openForThomas`.
2. **Discovery pass** (machine-only): locate the merlin/AI-Council output guideline (F014); confirm
   canonical repo/owner; confirm whether the lane kernel is the first-executable architecture or
   deferred infra.
3. **Wire capability-first execution**: build_engine/gateway consult `capabilities.py` and invoke a
   *resolved adapter* (authenticated agent CLI / local model / managed) — replacing the
   anthropic-default and any key-gate language.
4. **Prove ONE first executable**: a small real Platynum feature built through SI from a minimal
   prompt, from a recorded baseline, no manual implementation — with full evidence.
5. Only then decide whether the lane kernel graduates from QUARANTINE to KEEP.

## 7. Requires Thomas (blocking decisions)
- Accept/adjust the provisional **north star** and **first-executable target** (a concrete small
  feature).
- Decide the **lane-kernel disposition** (first-executable architecture vs deferred infra).
- Decide **canonical repo/owner** (consolidate SI + Platynum ownership?).
- For the real (non-deterministic) speedrun: make a **reasoning adapter available** (install/auth an
  agent CLI or local model, or choose the managed path). Deterministic conformance needs none.

## 8. Sufficiently supported to proceed automatically (once implementation is unfrozen)
- Discovery pass (read-only). · Wiring build_engine/gateway to the existing resolver. · Removing the
  inert Platynum-local prompts. · Encoding D1–D12 as fail-closed checks.

## 9. Truthfulness
No runtime feature was implemented in this pass. No facts, statuses, tests, commits, or metrics were
fabricated — every baseline and capability figure came from a command that ran (git, capabilities.py).
Contradictions are preserved, not silently resolved.
