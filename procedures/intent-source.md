# Intent Source Procedure

## Purpose

Allow `integrate` to materialize a new capability from a user-described need even when no existing skill/system source exists.

An intent source describes **what should exist**, not an implementation that must be preserved. It enters the same semantic/topic integration pipeline as other sources, but it has no pre-existing runtime contract unless the intent explicitly requires one.

## Input modes

### Existing Markdown intent

A positional Markdown file MAY be used directly:

```text
/skill-recomposer integrate ./my-intent.md
```

Prefer an explicit frontmatter marker when authoring such files manually:

```yaml
---
kind: skill-recomposer-intent
version: 1
---
```

The marker is recommended, not mandatory.

When a supplied Markdown file has no marker, classify it as an intent source when its primary content describes desired future capability/behavior rather than an existing skill-system artifact to preserve. Do not misclassify a real command, rule, agent definition, skill file, or other recognized host artifact merely because it is Markdown.

If classification remains materially ambiguous, ask one focused clarification before mutation rather than inventing source semantics.

### Interactive intent interview

When `integrate` receives no positional source, start an interactive clarification session.

Use the host's interactive question mechanism when available; otherwise ask directly in the current Claude Code session.

Ask only for information that is still needed. Do not force a fixed questionnaire when the user's initial answer already establishes the requirement.

The interview should converge on:

- desired capability/outcome;
- when it should apply or be invoked;
- expected behavior;
- important constraints and prohibitions;
- non-goals or boundaries when material;
- required inputs/outputs when relevant;
- whether explicit runtime surfaces are required (command, agent, hook, script, config, adapter, evaluation, or other host artifact);
- compatibility/interface requirements when relevant;
- concrete examples or acceptance criteria when they materially reduce ambiguity;
- optional topic preference when the user has one and `--topic` was not already supplied.

Do not ask implementation-detail questions the recomposer can safely derive itself.

## Canonical intent document

Normalize either input mode into a Markdown intent document with this shape, omitting empty optional sections:

```markdown
---
kind: skill-recomposer-intent
version: 1
---

# Intent

## Goal
...

## Activation / Use cases
...

## Desired behavior
...

## Constraints
...

## Non-goals
...

## Runtime requirements
...

## Compatibility requirements
...

## Examples / Acceptance criteria
...
```

The document MUST express user intent faithfully without prematurely inventing topic structure, skill boundaries, implementation files, or runtime machinery.

## Storage

For an interactive interview, capture the document in memory first. Plan its creation under the path below, include that creation in the operation patch, and persist it only during the transactional apply step:

```text
<STATE_ROOT>/intents/<intent-id>.md
```

This location is outside active skill/plugin discovery surfaces.

During `--dry-run`, do not write this document; keep it in memory and report the content and path that would be created.

User-supplied intent files remain in place and MUST NOT be modified, auto-deleted, or included in the operation patch.

Generated interactive intent documents are operation-owned state: record their creation in operation history and include it in the operation patch so rollback removes them. Outside rollback, retain them as provenance/history inputs unless a future policy explicitly garbage-collects them while preserving equivalent durable lineage.

## Source semantics

Classify the canonical document as `intent-source`.

Intent sources:

- are eligible only for `integrate`, not `recompose`;
- are never treated as recomposition-managed target artifacts;
- are never auto-deleted as disposable source skills;
- do not carry runtime contracts merely because they mention an outcome;
- MAY request creation of runtime artifacts explicitly or imply them strongly enough to require clarification/analysis;
- participate in semantic decomposition, topic routing, style normalization, policy construction, impact analysis, validation, and normal transaction handling.

If the intent requires commands/agents/hooks/scripts/configs/etc., enable only the corresponding analysis/creation tracks needed to satisfy that requirement.

## Topic routing

After intent normalization, use the ordinary `integrate` topic-routing rules:

- an explicit `--topic` is a subtree boundary, not a placement bias;
- otherwise search globally leaf-first;
- fragments may distribute across compatible descendant topics/skills;
- create new skills/topics only where necessary;
- create a new root topic when no existing topic can cover the intent adequately.

## Provenance

Use a durable lineage descriptor such as:

```text
intent-file:<normalized-path>#sha256:<hash>
```

or for interactive intents:

```text
intent:<intent-id>#sha256:<hash>
```

The generated target artifacts should retain this lineage without exposing it in user/model-facing runtime content unless functionally required.
