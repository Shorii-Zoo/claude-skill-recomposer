# Semantic Analysis Procedure

## Inventory input

Consume the source map from `procedures/source-discovery.md`. Deep-read semantic artifacts and materially relevant owned references; do not re-scan unrelated repository-development files.

Extract near-atomic semantic units with stable temporary ids and provenance.

Useful unit types include routing trigger, goal, fact, concept, definition, heuristic, methodology, preference, default, constraint, prohibition, exception, decision rule, precedence, workflow step, validation rule, quality criterion, example, template, tooling instruction, and reference material.

## Layer classification

Classify each semantic unit primarily as `KNOWLEDGE`, `POLICY`, `PROCEDURE`, `ROUTING`, or `RESOURCE`. Split mixed-purpose statements when needed.

Active-artifact runtime contracts are analyzed separately by `procedures/behavior-contracts.md`; do not flatten them into semantic units.

## Canonical normalization

Normalize semantics in English before comparison. Preserve scope, modality, conditions, exceptions, ordering, precedence, certainty, and purpose.

## Relationship taxonomy

Classify materially related units as:

- equivalent;
- overlapping;
- complementary;
- specialization;
- conditional divergence;
- methodological divergence;
- preference divergence;
- objective contradiction;
- operational conflict;
- unrelated.

## Activation signatures

For each candidate semantic cluster, identify intent, task type, task phase, input/output type, capability, condition, methodology, project policy, user preference, operational context, and activation mode when relevant.

## Candidate focused skills

Cluster primarily by activation overlap, capability coherence, workflow coherence, policy coherence, independent applicability, and progressive-disclosure value.

Do not mechanically merge merely because skills frequently co-activate.

Use the two-way test:

- Would a reasonable task often require A without B?
- Would a reasonable task often require B without A?

Also consider context size, specialized references, independent analysis axes, reuse, routing clarity, policy independence, and runtime graph boundaries.
