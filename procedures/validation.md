# Validation & Context-Budget Heuristics

## Semantic integrity

Validate:

- registry against schema;
- registry ↔ filesystem consistency;
- provenance and output fingerprints;
- topic containment and membership;
- glossary existence/inheritance/conflicts;
- inherited topic invariants;
- dependency graph targets and invalid cycles;
- skill routing boundaries;
- operational determinism;
- Knowledge/Policy/Procedure separation;
- style/structure consistency;
- broken references/paths;
- stale/orphaned generated artifacts.

## Runtime integrity

When active artifacts exist, `procedures/runtime-validation.md` is mandatory before destructive commit.

Semantic correctness alone cannot validate commands, agents, hooks, scripts, configs, adapters, or other active surfaces.

## Intent satisfaction

When integration uses an intent source, validate the candidate result against the canonical intent document before commit. Check that:

- stated goals and required use cases are covered;
- explicit constraints/prohibitions are preserved;
- non-goals were not accidentally expanded into scope;
- requested interfaces/runtime surfaces exist when required and unnecessary ones were not invented;
- acceptance examples/criteria are satisfied where testable;
- material unresolved choices were clarified rather than silently guessed.

Intent validation supplements semantic/runtime validation; it does not replace them.


## Context-size heuristics

Do not enforce arbitrary line limits as correctness rules, but flag likely context inefficiency.

Consider resegmentation when:

- a routable skill contains substantial conditional knowledge that can be disclosed;
- policy contains unrelated clusters;
- procedure combines independent workflows;
- a reference contains several independently retrievable domains;
- always-loaded routing/rule text is verbose relative to its trigger value;
- a model-invoked component's description/routing surface is broader than necessary;
- routine activation loads large irrelevant portions.

Prefer meaningful retrieval boundaries, direct references, and deterministic scripts for repeatable mechanics where appropriate.

## Routing validation

Test representative positive, multi-skill, boundary, methodology, user-preference, contradiction, specialized-knowledge, and negative/no-trigger tasks.

## Final determinism test

Search for simultaneously applicable incompatible instructions without precedence, selection criteria, defaults, or explicit overrides.

## Final destructive gate

Do not delete source material until semantic validation, required runtime validation, dependency rewrite validation, and transaction preconditions all pass.
