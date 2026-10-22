# Impact Analysis Before Modification

Run before any mutation of managed semantic or active artifacts.

## Determine affected closure

Identify:

- directly modified artifacts/topics;
- descendant skills inheriting glossary/style/invariants;
- incoming and outgoing graph edges;
- reverse callers/consumers of renamed/moved/replaced artifacts;
- entrypoints and adapters exposing affected capabilities;
- scripts/handlers/configs referenced by affected artifacts;
- tests/evals covering changed contracts;
- shared references and active support;
- registry/provenance/fingerprints;
- host discovery declarations and path assumptions;
- routing collisions likely to change.

## Classify impact

For each affected entity classify one or more:

- no semantic impact;
- style/terminology-only;
- routing;
- policy;
- knowledge dependency;
- runtime contract;
- invocation/public interface;
- host/discovery;
- structural/hierarchy;
- validation/evaluation;
- destructive/deletion.

## Mutation rule

Do not modify an entity merely because it appears in the closure. Modify only where required for correctness, consistency, or an explicitly chosen canonicalization.

This is especially strict for existing topic boundaries and stable public/runtime interfaces during `integrate`.

## Blocking impact

A planned mutation is blocked until every runtime-critical consumer has a migration, preserved target, or compatibility shim.

## Report

Mutating operations SHOULD include a concise impact summary before commit or in dry-run output.
