# Operation: recompose

## Invocation

```text
/skill-recomposer recompose <source-1> <source-2> ... [--dry-run]
```

If no subcommand is supplied, `recompose` remains the default.

A source may be a single local skill directory, command/agent bundle, broader skill-system root, or supported GitHub repository/subtree/file URL. Explicit roots define the maximum source scope.

`recompose` requires existing source material. User intent documents and no-argument interactive intent capture belong to `integrate`, not `recompose`.

## Phase 0 — normalize, discover, and plan

For supported GitHub URLs, load `procedures/remote-source-resolution.md` first and replace the remote input with its isolated local resolved source root plus durable provenance descriptor.

Then load:

- `procedures/source-discovery.md`
- `procedures/complexity-planning.md`

Build the source map and complexity plan before deep analysis. Then load only the artifact modules/procedures selected by that plan.

## Semantic modules

When semantic skill/rule/reference material exists, load:

- `core/style-structure.md`
- `core/glossary.md`
- `procedures/semantic-analysis.md`
- `procedures/conflict-resolution.md` when needed;
- `procedures/topic-routing.md`.

## Runtime modules

When active artifacts exist, load as selected:

- `core/host-layout.md`;
- relevant `artifact-types/*.md`;
- `procedures/behavior-contracts.md`;
- `procedures/dependency-rewrite.md` when any active target is renamed, moved, split, merged, wrapped, superseded, or replaced;
- `procedures/runtime-validation.md`.

Always load for mutation planning:

- `procedures/impact-analysis.md`;
- `procedures/validation.md`;
- `procedures/patching.md` unless dry-run;
- `procedures/garbage-collection.md` unless dry-run.

## Behavior

Validate that explicit existing sources are ordinary non-recomposition outputs.

Explicit local inputs classified `disposable-source-unit` MUST be deleted automatically after successful validated commit under `procedures/source-discovery.md`. The `recompose` invocation itself authorizes deletion; require no second confirmation, deletion flag, or separate consent. Dry-run, failed validation, and uncommitted operations leave sources untouched. All source-discovery safety exceptions remain in force.

Recompose the supplied material into focused semantic capabilities plus the minimum active/support artifacts needed to preserve behavior. Source boundaries are not authoritative, but runtime contracts are.

Construct or update:

- focused skills and Knowledge/Policy/Procedure separation;
- topic hierarchy, invariants, glossaries, and style profiles;
- commands/agents/hooks/scripts/configs/rules/references/evals/adapters when present and necessary;
- artifact and dependency graph;
- compatibility shims when justified;
- provenance and supersession metadata.

A semantic-only source should remain a semantic-only recomposition unless new runtime machinery is genuinely required.

## Delegation

Use the complexity plan to delegate independent source maps, semantic clusters, runtime artifact families, and final validation. Keep architecture synthesis and mutation centralized.

## Destructive behavior

Delete an original local source root only after successful committed validation **and** only when source discovery marked that explicit root `disposable-source-unit`.

Never auto-delete an entire repository/broad source checkout merely because it was analyzed.

Remote GitHub sources are not deleted; resolver-owned temporary checkouts are cleaned after the run.

Dry-run reports the proposed architecture, artifact graph, migrations, compatibility surfaces, and source-deletion/cleanup plan without mutation.
