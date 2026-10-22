# Garbage Collection

Run only after successful target-state validation and permitted source deletion.

## Reachability first

Before deleting any managed artifact, verify it is unreachable from:

- public/user/model/event entrypoints;
- runtime-critical dependency edges;
- host manifests/discovery config;
- active scripts/handlers/agents;
- semantic skills/references;
- tests/evals that still encode retained behavior;
- compatibility shims;
- topic/shared-knowledge ownership.

## Safe candidates

Safely remove only artifacts proven unused or superseded, such as:

- empty topics with no semantic purpose;
- unreferenced generated shared references;
- dead glossary entries when confidently detectable;
- stale graph edges to entities removed in the same transaction;
- obsolete compatibility shims after all consumers migrate;
- superseded scripts/configs with no callers;
- temporary staging artifacts;
- obsolete provenance metadata for removed entities.

## Restrictions

Do NOT remove rollback patches as ordinary GC.

Do NOT remove user-authored or persisted interactive intent documents as ordinary artifact GC; they are operation input/provenance evidence, not managed runtime artifacts.

Do NOT remove a topic merely because it has one child if it remains a meaningful scope/invariant/glossary boundary.

Do NOT delete unknown or potentially active artifacts. Report them instead.
