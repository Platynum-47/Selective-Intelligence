---
name: si-intake
description: Start a run in simple words, capture the real outcome, and send a clean packet to the planner.
license: CC0-1.0
metadata:
  version: "0.1.0"
  parent: selective-intelligence
  audience: "plain-language"
---

# SI Sub-Skill: Intake

## What this skill does (plain language)
It asks one very simple question: "What do you want to make?"
Then it turns the answer into a short goal packet for the next agent.

## Inputs
- A user message that starts a project
- Optional seed: idea, URL, repo note, image, or short brief

## How it works
1. Read the seed and infer the biggest real goal.
2. If the goal is missing, ask only this one question:
   - "What outcome do you want to create or complete?"
3. Save any plain, reversible assumption used to continue.
4. Return a one-screen Intake Packet:
   - Project name (or temporary name if not given)
   - Seed summary
   - What is definitely true vs what is still guessed
   - One next step for the planner

## Output
Return:
- `outcome` (plain sentence)
- `assumptions` (very short list)
- `constraints` (hard limits like safety, money, permissions)
- `next_skill`: `si-planner`
- `next_step_id`

## Non-negotiable rules
- Ask only one question unless a real safety, money, or permission decision blocks progress.
- Never ask for keys, tokens, CLI commands, or auth setup in this phase.
- Keep language simple and easy for non-developers.
