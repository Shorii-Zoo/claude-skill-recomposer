# Complexity & Analysis Planning

## Purpose

Select the minimum analysis tracks needed for the discovered source system or user intent.

## Base semantic track

Every source containing semantic instructions, knowledge, or an intent specification uses:

- `procedures/semantic-analysis.md`;
- `procedures/conflict-resolution.md` when overlapping/competing policy is detected against existing targets or among sources;
- applicable `artifact-types/skill.md`, `rule.md`, or `reference.md` modules only when actual target/source artifact analysis requires them.

An intent source begins as semantic requirements, not as a pre-existing `skill` artifact.

## Conditional tracks

Enable only when inventory or explicit intent requires them:

| Signal | Load |
| --- | --- |
| explicit/user entrypoints exist or are requested | `artifact-types/command.md`, `procedures/behavior-contracts.md` |
| subagents/delegated personas exist or are requested | `artifact-types/agent.md`, `procedures/behavior-contracts.md` |
| lifecycle/event handlers exist or are requested | `artifact-types/hook.md`, `procedures/behavior-contracts.md`, `procedures/runtime-validation.md` |
| executable helpers exist or are clearly required | `artifact-types/script.md`, `procedures/behavior-contracts.md`, `procedures/runtime-validation.md` |
| manifests/MCP/LSP/runtime config exists or is required | `artifact-types/config.md`, `core/host-layout.md`, `procedures/runtime-validation.md` |
| persistent/broad rules exist or are requested | `artifact-types/rule.md` |
| tests/evals/fixtures exist or acceptance validation requires them | `artifact-types/evaluation.md`, `procedures/runtime-validation.md` |
| host-specific wrappers/adapters exist or compatibility requires them | `artifact-types/adapter.md`, `core/host-layout.md`, `procedures/behavior-contracts.md` |
| templates/assets/support docs exist or are needed | `artifact-types/reference.md` |
| unclassified existing material | `artifact-types/generic.md` |
| renamed/moved active artifacts | `procedures/dependency-rewrite.md`, `core/host-layout.md` |

Do not enable runtime tracks merely because an intent could hypothetically be implemented with runtime machinery. Enable them only when the required behavior/interface makes them necessary.

For `recompose`/`integrate`, topic routing, impact analysis, validation, and transaction procedures still apply according to the operation file.

## Complexity tiers

Use qualitative tiers only to plan work:

- **semantic-only** — passive knowledge/instructions or an intent requiring no active runtime graph;
- **workflow** — routable skills/commands and references, limited active dependencies;
- **runtime** — scripts, agents, hooks, configs, adapters, or nontrivial invocation graph;
- **system** — several active artifact families, cross-host adapters, shared runtime components, or broad dependency closure.

The tier does not change correctness requirements; it controls context and delegation.

## Intent planning

For an intent source, report separately:

- semantic capabilities to integrate;
- existing managed targets likely reusable;
- new artifact families genuinely required;
- unresolved behavior/interface questions that must be clarified before commit;
- acceptance criteria available for validation.

Prefer existing compatible capabilities and minimum new machinery.

## Delegation plan

For `runtime` or `system` sources, partition independent analysis by artifact family or source root and use `core/delegation.md`.

For `semantic-only`, avoid spawning runtime analyzers.

Interactive user clarification remains in the main session; do not delegate user-facing questioning to a subagent that cannot reliably interact with the user.

## Output

Return:

- tier;
- artifact modules to load;
- reusable procedures to load;
- recommended subagent tasks;
- runtime-critical areas requiring independent validation;
- for intents, required creations vs reusable existing targets and any unresolved questions.
