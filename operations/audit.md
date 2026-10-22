# Operation: audit

## Invocation

```text
/skill-recomposer audit <topic-id-or-name>
/skill-recomposer audit <topic-id-or-name> --fix [--dry-run]
```

## Planning

Load the core kernel, `core/style-structure.md`, `core/glossary.md`, `procedures/impact-analysis.md`, `procedures/topic-routing.md`, and `procedures/validation.md`.

Use the registry to determine artifact kinds in the selected subtree. Load only matching `artifact-types/*.md` modules and runtime procedures.

If active artifacts exist, also load `core/host-layout.md`, `procedures/behavior-contracts.md`, and `procedures/runtime-validation.md`. Load `procedures/dependency-rewrite.md` only if `--fix` would rename, move, split, merge, wrap, supersede, or replace active artifacts.

## Report-only mode

Default audit is read-only. Analyze the subtree for:

- poor skill boundaries and routing ambiguity;
- unresolved policy conflicts or Knowledge/Policy leakage;
- stale glossary/invariant/style structure;
- dependency and supersession problems;
- context inefficiency and hierarchy imbalance;
- broken/duplicated entrypoints;
- runtime-contract drift;
- stale command/agent/hook/script/config references;
- invalid host placement;
- dead or untested runtime support;
- unknown artifacts whose ownership/role is unclear.

Topic rebalance analysis is included.

## --fix

`--fix` MAY modify managed semantic and active artifacts, topic structure, glossaries, invariants, graph edges, registry data, and shared references.

Non-dry-run `--fix` is a mutating operation: it requires an existing registry, creates an operation patch, and never seeds a new registry. If state is missing, report it and stop.

A parseable registry that is invalid or inconsistent MAY be diagnosed and repaired transactionally. The operation patch MUST retain the original invalid registry bytes as its before-image for forensics, so rollback and recovery use the patch payload and never depend on an external snapshot. Repair requires a parsed JSON mapping and an `operations` list whose existing history can be preserved unchanged; otherwise stop without mutation. Per `core/registry.md`, restoration uses the recorded managed projection excluding top-level `operations`, preserves known invalid managed fields, and merges the live append-only ledger; never whole-file overwrite the registry or reset history. Before repair, also capture the invalid registry in a readable, recoverable snapshot stored outside the patch payload for diagnosis. If the registry is unreadable or cannot be recovered, report it and stop without mutation.

Apply minimal necessary change and full impact analysis. Runtime/public interfaces must follow the same contract migration rules as `integrate`.

For non-dry-run fixes, load `procedures/patching.md` and `procedures/garbage-collection.md`.

`--fix --dry-run` is read-only and creates no state. It may inspect a parseable registry and report exact proposed repairs without mutation, and reports unreadable or unrecoverable registry state as blocking.
