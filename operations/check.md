# Operation: check

## Invocation

```text
/skill-recomposer check [<topic-id-or-name>]
```

No argument checks the entire managed library.

## Load

Load the core kernel plus `core/style-structure.md`, `core/glossary.md`, and `procedures/validation.md`.

Inspect registry artifact kinds for the selected scope and load only matching artifact modules. If active artifacts exist, load `core/host-layout.md` and `procedures/runtime-validation.md`.

Load `procedures/impact-analysis.md` only when needed to explain consequences.

## Behavior

Read-only integrity checker. Never mutate files, registry, provenance, topics, or history. If state is missing, report that no managed state exists and do not initialize it.

Check:

- registry/filesystem/provenance consistency;
- topic/glossary/invariant/style integrity;
- dependency graph and supersession integrity;
- routing and operational-policy ambiguity;
- host/discovery placement;
- commands/agents/hooks/scripts/config/reference resolution;
- runtime-critical contract links;
- executable modes and structured config parseability when applicable;
- eval/test target integrity;
- orphaned/dead artifacts;
- context-budget concerns;
- unknown artifacts needing audit.

Report by severity and affected entities with targeted corrective action.
