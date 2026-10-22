# Skill Recomposition — Specification Index

This file is a compatibility index. Do not load the whole specification by default.

## Core kernel

Load for every operation:

- `core/principles.md`
- `core/architecture.md`
- `core/artifact-model.md`
- `core/registry.md`
- `core/dependencies.md`
- `core/transactions.md`
- `core/provenance.md`
- `core/delegation.md`

Load `core/style-structure.md`, `core/glossary.md`, and `core/host-layout.md` only when the selected operation needs them.

## Operations

- `operations/recompose.md`
- `operations/integrate.md`
- `operations/audit.md`
- `operations/check.md`
- `operations/rollback.md`

## Discovery and planning

- `procedures/remote-source-resolution.md` — load only when a supplied source is a supported GitHub URL
- `procedures/intent-source.md` — load only for `integrate` intent Markdown or no-source interactive intent capture
- `procedures/source-discovery.md`
- `procedures/complexity-planning.md`

Normalize remote inputs and `integrate` intent inputs first when present, then run source discovery and complexity planning before loading artifact-specific analyzers.

## Artifact-specific modules

Load only for artifact kinds actually discovered or affected:

- `artifact-types/skill.md`
- `artifact-types/command.md`
- `artifact-types/agent.md`
- `artifact-types/hook.md`
- `artifact-types/script.md`
- `artifact-types/config.md`
- `artifact-types/rule.md`
- `artifact-types/reference.md`
- `artifact-types/evaluation.md`
- `artifact-types/adapter.md`
- `artifact-types/generic.md`

## Reusable procedures

Load only when requested by an operation or complexity plan:

- `procedures/semantic-analysis.md`
- `procedures/conflict-resolution.md`
- `procedures/behavior-contracts.md`
- `procedures/topic-routing.md`
- `procedures/impact-analysis.md`
- `procedures/dependency-rewrite.md`
- `procedures/patching.md`
- `procedures/garbage-collection.md`
- `procedures/validation.md`
- `procedures/runtime-validation.md`

The skill entrypoint at `skills/skill-recomposer/SKILL.md` owns module selection. Plugin installs resolve implementation resources through `${CLAUDE_PLUGIN_ROOT}`; manual installs use the documented fallback path.

## Templates

- `templates/intent.md` — optional starter for user-authored integration intent documents
