# Non-Developer Surface

Selective Intelligence builds for vibe coders, not developers. The user never has to do a
developer's job to use what you build. This is a hard gate: if a surface, connector, or step
requires developer knowledge or credential handling, it is wrong — fix the architecture, do not
hand the task to the user.

## Contents

- [The rule](#the-rule)
- [The architecture principle](#the-architecture-principle)
- [Language](#language)
- [Enforcement](#enforcement)
- [Failure harvested](#failure-harvested)

## The rule

Never require the user to obtain, paste, or manage any of:

- API keys, access tokens, or secrets — including "personal access tokens", OAuth client
  secrets, or picking "repo scope";
- environment variables, `.env` files, or config files;
- CLI commands, package installs, or build steps;
- provider dashboards, developer settings, or scope/permission jargon.

Replace each with a one-click flow ("Connect GitHub" → authorize → done) or a plain-language
choice. The mechanics (tokens, scopes, exchange) happen behind the surface; the user sees a
button and an outcome.

## The architecture principle

If a capability cannot be delivered without exposing developer mechanics, that is an
**architecture gap to fix — not a step to hand the user.** A pure-static / no-backend design
that forces the user to paste a token has chosen developer burden over user experience; add the
minimal broker or one-click flow instead. Never ship the developer wall as the user path — and
never disguise it as the "advanced" path while leaving it as the only path.

## Language

- Plain language only on any user-facing surface. No routing, API, dependency, token, scope,
  env, or CLI vocabulary.
- Explain outcomes ("your changes are live"), not mechanics ("committed SHA … triggered CI").

## Enforcement

This gate is not satisfied by being written here. It is enforced by:

- an eval case that **fails** when a build asks the user for a token, key, scope, env var, or CLI
  command;
- the product surface (e.g., Platynum-47) refusing to present such a step to the user.

A prose rule the model can read and violate is not enforcement; the check and the product are.
See [first-checkpoint.md](first-checkpoint.md) for why documented ≠ enforced.

## Failure harvested

Origin: a GitHub connector shipped a "paste a personal access token (repo scope)" field into a
non-developer product. That is the exact wall this gate exists to stop.
