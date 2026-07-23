# Changelog

All notable behavior changes to Selective Intelligence are recorded here.

## Unreleased

- Added a consequence-scaled friction ladder so ceremony matches stakes instead of an up-front mode choice: a Tier 0 scratch lane that builds throwaway, local, single-session prototypes immediately with no Intent Lock, Council, or Start Pack; an explicit Tier 0 → Tier 1 promotion gate (persistence, shared state, real users, money, external deployment, or intent to keep) that triggers a brief retroactive Intent Lock and one Objector pass; and Tier 1 keeping the full Start-mode contract unchanged. The two non-negotiable guardrails — no unauthorized external effect, no unproven completion claim — hold at every tier. Documented in `references/friction-ladder.md` with a Tier 0 short-circuit in `SKILL.md` and `JUMPSTART.md`, and surfaced in both `README.md` files.
- Added an output-economy rule so agent responses spend tokens on building, not narration: lead with result and proof (repo, branch, what changed, pass/fail), reference artifacts by path instead of pasting them, and stop repeating the request or narrating unchosen options — without dropping proof, blockers, or required approvals. Documented in `SKILL.md` and `references/ui-ux-and-output.md`.
- Added a **first-checkpoint gate**: any build-shaped request must emit a locked, information-complete, full-scope intent checkpoint (recovered full intent, whole-product decomposition with proof, canonical reuse map, build sequence, authority split) before any code, and must not start any part until every input needed to perform all of it is in hand. Genuine unknowns are resolved in one consolidated up-front pass, never trickle-asked. Named guards for the mined drift classes (scope-reduction-as-completion, single-thread default, ask-instead-of-recover, vibe-sprint-under-deadline, literal-ask-over-full-intent, trim-without-authority, partial-start-before-info-complete) and a correction-rounds-to-correct-checkpoint metric. Documented in `references/first-checkpoint.md`, gated in `SKILL.md`, with an eval case in `evals/evals.json`.
- Added **time-awareness** doctrine: timestamp durable work in UTC (ISO 8601), track elapsed time and durations, convert relative dates to absolute, flag stale facts, carry wall-clock into handoffs/resumes, and never fabricate or backdate. Documented in `references/time-awareness.md`.
- Added a **non-developer-surface gate**: never require the user to obtain, paste, or manage a token, API key, scope, env var, CLI command, or config file — hide all mechanics behind one-click flows, and treat any capability that cannot be delivered without them as an architecture gap to fix, not a step for the user. Made the first-checkpoint gate unconditional (the first move, not skippable), made **Tier 1 the default** for anything real (a user other than the author, persistence, shipping, or intent to keep), and stated plainly that gates bind only when enforced by the eval suite and the wrapping product — documented is not enforced. Documented in `references/non-developer-surface.md`, wired into `SKILL.md`, with an eval case in `evals/evals.json`. Harvested from a real failure (a GitHub connector that shipped a "paste a personal access token" field into a non-developer product). Also defined the **minimal human layer**: across a whole build the user should only ever answer a genuinely material question, take the alignment/authority steps the AI cannot self-grant, connect their own third-party sources in one click, or take an action only a human can — everything else is the AI's job.
- Made the deterministic eval controls **cross-platform**: the feedback-store permission and symlink self-tests are POSIX-specific and previously crashed on Windows; they now guard on `os.name`/symlink support and run everywhere. POSIX release behavior and recorded control identity are unchanged.
- Added the **canonical acceptance benchmark** (`acceptance-invent-si-with-user-layer`): the seed "Invent Selective Intelligence with a user layer" must produce this entire doctrine + tiered system + repo package — the SI engine and a non-developer user layer that runs it — as the **first deliverable, uncorrected**. Correction-rounds-to-correct-deliverable approaching zero is the top-level measure SI is graded against. It is a declaration until the model-in-the-loop runner can grade it; defining the benchmark is not passing it, and the session that produced it failed the benchmark by requiring extensive correction.
- Added `scripts/eval_runner.py` — the **model-in-the-loop eval runner** the skill's own docs named as the blocker. Dependency-free (stdlib `urllib`), bring-your-own key via `ANTHROPIC_API_KEY` (the human-layer connect step), provider-agnostic with Anthropic implemented first, model-judged `must`/`must_not`, and timestamped, model-identified evidence. Runs a dry run (no network) when no key is set. The runner now exists; producing evidence needs only a model key — turning the eval cases from declarations into gradable tests.
- Added the **false-choice-when-both-required** guard: offering the user an either/or between options that are all needed is itself a failure — do them all; only a genuine, mutually exclusive, outcome-changing fork is worth asking.
- Docs plus new eval cases, a cross-platform eval fix, and the new eval runner (code); schemas, `VERSION`, and the JumpStart protocol version are unchanged pending a release run. New eval cases remain declarations until the runner records reproducible model/client evidence.

## 0.2.0 - 2026-07-22

- Added `JUMPSTART.md`, a zero-install cold-start contract that can be intentionally uploaded or pasted into ChatGPT with an idea, URL, file, note, or repository.
- Added ChatGPT Project guidance for one continuing product or brand per Project, project-only memory when appropriate at creation, and privacy-bounded promotion of approved or hard-won responses into Project sources.
- Added the Guided Council workflow with capability-triggered Worker, Objector, Aligner, and optional Reserve agents plus a separate-context fallback that keeps additional AI providers optional.
- Added strict provider-neutral Council packets, default-deny action permissions, exact approval receipts, data-boundary checks, integer-minor-unit budget locks, specific objections, evidence-based alignment, portable resume state, and hash-chained local provenance.
- Added a dependency-free Council CLI and deterministic adversarial controls while preserving the Start Pack schema and validator at component version 0.1.1.
- Decoupled skill, Start Pack schema/validator, and Council protocol versions in release validation; every declared JSON Schema is now validated and packaged explicitly.
- Preserved all prior operating modes, behavioral declarations, deterministic result history, privacy-safe feedback behavior, free CC0 distribution, and model-neutral truth standards.
- Kept public-release claims gated on reproducible fresh-context model/client evidence; deterministic local completion alone remains a release candidate rather than proof of universal behavior.
- Added branch-per-slice and chat-branch pairing guidance: pair a bounded git branch/PR with a bounded or forked chat session so a new bounded task starts from a clean, low-token context instead of an ever-growing thread, while still resuming from the authoritative lock and evidence rather than reconstructed memory.

## 0.1.1 - 2026-07-22

- Made every seal transactional: an invalid prospective control graph is rejected without rewriting the Start Pack.
- Bound amendments to decision owners captured in the prior seal and required registered approval evidence.
- Required independent reviews to identify a distinct reviewer, exact revision, scope, timezone-aware timestamp, and registered evidence artifact.
- Enforced the portable independent-review object, required fields, and status enum for every Start Pack, including low-risk unverified packs.
- Added requirement-cycle and governing-source validation parity controls.
- Preserved parent-directory permissions for custom feedback stores while retaining private defaults for managed stores.
- Replaced implicit packaging discovery with an exact reviewed release manifest and rejection of undeclared files, corrupt schemas, and stale or failing result records.
- Classified prompt behavior cases as declarations only; public release now requires reproducible model/client evidence rather than inferred coverage.
- Bound recorded deterministic-control counts and identities to the controls executed by release doctor; parsed model-run artifacts for matching skill, version, model/client, timestamp, and complete per-case passes; and rejected intermediate release-path symlinks.
- Corrected the retained 0.1.0 result record so its deterministic fixture run is not presented as model/client behavior coverage.
- Declared the actual Python 3.10+ runtime floor and added safe update and uninstall guidance.
- Kept 0.1.0 Start Packs fail-closed until their new authority, review, approval-evidence, and seal-history fields are explicitly migrated; changing only the validator version is not a migration.
- Expanded implicit triggers for interrupted-project recovery, UI/UX realignment, PDF-first collateral, and privacy-safe low-input feedback after fresh-context misses.
- Assigned Platynum Standard's canonical public repository and adopted GitHub's discoverable `skills/selective-intelligence/` source layout without creating adapter copies.

## 0.1.0 - 2026-07-22

- Established the model-neutral actual-intent, evidence, reuse, repository-realignment, UI/UX, and PDF-first contracts.
- Added Start mode with proportional Definition, Build, As-Built, and release locks.
- Added dependency-free Start Pack initialization, validation, drift detection, convergence, sealing, status, and resume controls.
- Added non-repeatable phase transitions, semantic contract digests, per-seal artifact and invalidation ledgers, and narrow interruption/resume checkpoints.
- Added parallel-owner, stale-fact, semantic-change, operational-risk, evidence-invalidation, and independent-review gates.
- Added privacy-preserving local feedback signals and aggregate learning metrics.
- Added portable schema, interoperability, distribution, discoverability, free-use, and optional-support contracts.
