# Selective Intelligence

Selective Intelligence—formerly Selective Inheritance—is a free, portable Agent Skill that turns plain-language intent and minimal trustworthy input into complete, evidence-grounded outcomes. It helps vibe coders plan new products, audit codebases, repair drift, find missing or unrouted features, reuse canonical architecture, verify UI/UX, and stop AI from calling partial work complete.

Published by [Platynum Standard](https://github.com/Platynum-Standard). The canonical source is [Platynum-Standard/Selective-Intelligence](https://github.com/Platynum-Standard/Selective-Intelligence).

## Start without installing anything

The hardest part of vibe coding is often the blank chat at the beginning. Use [JUMPSTART.md](JUMPSTART.md) to remove that cold start:

1. Download or copy `JUMPSTART.md`.
2. Upload or paste it into ChatGPT with whatever you have—an idea, URL, file, note, screenshot, or existing repository. If you have nothing else yet, JumpStart asks one plain-language outcome question.
3. For continuing product or brand work, follow its prompt to create or open one dedicated ChatGPT Project. Choose project-only memory at creation when isolation is appropriate and the option is available.
4. Let it recover intent, choose the smallest sufficient setup, separate the Worker, Objector, and Aligner roles, execute authorized work, challenge the result, correct valid objections, and leave a resume state.

When the active ChatGPT environment can spawn distinct agents, JumpStart uses that capability automatically; another AI subscription is not required. When it cannot, the same roles run in separate sequential contexts. A second model remains an optional manual Objector, not a prerequisite.

Along the way, save an approved durable decision, reusable output, or hard-won correction as a Project source so later chats inherit the understanding. Before saving, check ownership and permission to retain it, whether the Project is shared, what data is permitted, and the applicable data-use setting. Do not save secrets, brainstorming, stale prices, false completion claims, or cross-project material.

Project sources are continuity aids, not proof: current locks, repository state, tests, and authoritative evidence still win.

Use it when you want an agent to:

- define a new product, smallest complete MVP, architecture, data, APIs, UI/UX, build order, and proof before coding;
- resume a project across models, agents, branches, or interrupted sessions without losing the governing truth;
- crawl a repository and reconcile intended behavior with routes, components, services, schemas, permissions, tests, deployment, and live surfaces;
- consolidate duplicate modules and place new work under clear canonical ownership;
- turn a URL or sparse brief into a complete profile, campaign, artifact, or system without inventing facts;
- generate precision flyers and text-bearing collateral as render-verified PDFs;
- learn from corrections and outcome signals without uploading prompts or personal data.

## Use in ChatGPT

[Open Selective Intelligence in ChatGPT](https://chatgpt.com/skills?skill_id=6a60f7ecb940819186be4dffa3094f85) when the skill is enabled for your account. Until a public listing is active, this route may return to the ChatGPT home page for other users.

Example requests:

- “Start this product. Lock the full first release, architecture, database, APIs, UI/UX, and proof before you build it.”
- “Crawl this repo, find drift, missing features, unrouted pages, duplicate systems, and finish the real user flow.”
- “Pick this project back up from its current lock without repeating work or trusting stale evidence.”
- “Use Selective Intelligence to audit and improve Selective Intelligence.”

## Portable installation

The canonical portable source is the complete [`skills/selective-intelligence/`](https://github.com/Platynum-Standard/Selective-Intelligence/tree/main/skills/selective-intelligence) directory. Keep that directory intact: `SKILL.md`, `agents/`, `references/`, `schemas/`, `scripts/`, `metadata/`, and `evals/` form one skill.

With GitHub CLI 2.90.0 or newer, preview and install it with:

```bash
gh skill preview Platynum-Standard/Selective-Intelligence selective-intelligence
gh skill install Platynum-Standard/Selective-Intelligence selective-intelligence
```

For a manual project-level installation, copy the canonical directory intact to `.agents/skills/selective-intelligence/`. A versioned release archive, once published, will extract as one complete `selective-intelligence/` directory.

Common project-level destinations are:

| Client family | Skill destination |
|---|---|
| Agent Skills-compatible clients, Codex, Cursor, Copilot, Gemini | `.agents/skills/selective-intelligence/` |
| Claude Code | `.claude/skills/selective-intelligence/` |
| Cursor alternative | `.cursor/skills/selective-intelligence/` |
| Gemini CLI alternative | `.gemini/skills/selective-intelligence/` |
| Kiro | `.kiro/skills/selective-intelligence/` |

Use the canonical repository or versioned release archive as the source for every destination. Client paths are adapters, not separate editions.

Filesystem access is required for repository and Start modes. Python 3.10 or newer runs the dependency-free validators. Live web evidence needs browser or network access. When a capability is unavailable, the skill narrows the blocker and preserves the same truth standard.

The current deterministic release-candidate evidence is recorded in [evals/results-0.2.0.json](evals/results-0.2.0.json). The prompt cases in `evals/evals.json` are declarations until a reproducible model/client runner records evidence. Public release remains blocked until that behavioral evaluation exists. The contract is model-neutral; equivalence across untested models is not claimed as proof.

### Update and uninstall

To update after publication, run `gh skill update selective-intelligence`, or obtain a newer versioned archive or canonical repository revision, verify its release checksum, and replace only the existing `selective-intelligence` skill directory at the destination you chose. Preserve any project-created `.selective-intelligence/` Start Packs and feedback stores; they are project data, not installed skill files.

Version 0.2.0 adds Council protocol 0.2.0 while preserving the Start Pack schema and validator at component version 0.1.1; existing 0.1.1 packs do not need a semantic migration merely to use the new skill. Version 0.1.1 deliberately does not reinterpret a Start Pack sealed by validator 0.1.0. Keep the 0.1.0 validator with an existing pack until its prior authority, amendment approvals, independent-review record, and seal-history snapshots have been explicitly migrated and resealed under 0.1.1. Do not change only `validator_version` and treat the result as migrated.

To uninstall, remove only the installed `selective-intelligence` skill directory from that documented destination. Do not delete a parent skills directory or any project `.selective-intelligence/` directory.

## GitHub visibility and repository isolation

Selective Intelligence may be published as a public repository on an existing GitHub account. This does not expose private repositories on that account.

Every repository that remains public is independently viewable, downloadable, forkable, and cloneable. GitHub has no public-but-non-cloneable, AI-only, or unlisted-public repository mode. If unrelated source must not be copied by unauthorized people, make that repository private before publishing this skill. For private repositories, use selected-repository access and least-privilege permissions where the integration supports them. A dedicated account or organization can improve brand and profile separation, but it cannot prevent copying of any repository that is public.

Assume anything previously public may already have been copied. Changing visibility does not recall local clones, and existing public forks can remain public in a separate network. Never commit secrets; rotate any credential exposed publicly. See GitHub's documentation for [repository visibility](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility), [cloning](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository), and [source archives](https://docs.github.com/en/repositories/working-with-files/using-files/downloading-source-code-archives).

## Free forever

The complete skill, validators, schemas, references, templates, evals, and updates are released under [CC0 1.0 Universal](LICENSE). Use, copy, modify, redistribute, or commercialize them without asking permission.

An optional Sway support link will be added only after the owner supplies the exact destination. Donations will never unlock features, change output quality, or become required for installation or updates.

See [distribution and discoverability](references/distribution-and-discoverability.md) for the public repository, release, integrity, and support-link contract.
