# Domain Docs

## Layout

This repo uses a single context: `GLOSSARY.md` at the repo root and architecture decision records in `docs/adr/`.

## Before exploring, read these

- Read the root `GLOSSARY.md`.
- Read ADRs in `docs/adr/` that touch the area you are about to work in.

If these files do not exist, proceed silently. The `/domain-modeling` skill creates them lazily when terms or decisions get resolved.

## Use the glossary's vocabulary

When naming a domain concept in an issue title, refactor proposal, hypothesis, or test name, use the glossary's term. If the needed concept is absent, reconsider whether the project uses that language or note the gap for `/domain-modeling`.

## Flag ADR conflicts

If a proposal contradicts an existing ADR, identify the ADR and explain why the decision should be reopened.
