# Delegation & Context Partitioning

## Goal

Keep the main session focused on synthesis and mutation while independent inspection work receives only the context it needs.

## Delegation policy

Use subagents when they reduce context or allow independent analysis. Do not create delegation merely for ceremony.

Good delegation units include:

- one explicit source root inventory;
- one artifact family within a large source;
- one semantic cluster;
- one runtime-contract family;
- one independent validation dimension.

## Available internal roles

The plugin ships read-only analysis agents:

- `source-cartographer` — filesystem/artifact map and ownership boundaries;
- `semantic-analyzer` — semantic units, conflicts, activation signatures, topic candidates;
- `artifact-analyzer` — runtime contract and dependency analysis for a specified artifact type;
- `system-validator` — independent candidate-state review.

Use them when available. If subagent execution is unavailable, run the same modules sequentially in the main session.

## Main-session responsibilities

The main session MUST retain responsibility for:

- final architecture decisions;
- conflict synthesis across analyzer outputs;
- topic selection and rebalancing;
- mutation plan;
- patch creation/commit ordering;
- destructive source deletion;
- final registry update.

Do not let independent subagents mutate overlapping targets.

## Complexity-driven plan

`procedures/complexity-planning.md` determines which analyzers and artifact modules are needed. A knowledge-only source should normally require semantic analysis only. A complex runtime bundle may fan out to several artifact analyzers plus a validator.

## Analyzer output

Delegated analyses SHOULD return compact structured findings, not rewritten files. Include artifact ids/paths, contracts, dependencies, conflicts, uncertainties, and recommended transformations.
