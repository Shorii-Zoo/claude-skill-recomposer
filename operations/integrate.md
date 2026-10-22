# Operation: integrate

## Invocation

Existing source material:

```text
/skill-recomposer integrate <source-1> [<source-2> ...] [--topic <topic-id-or-name>] [--dry-run]
```

A source may be a local skill/system path, a supported GitHub URL, or a Markdown intent document.

Interactive intent capture:

```text
/skill-recomposer integrate [--topic <topic-id-or-name>] [--dry-run]
```

When no positional source is supplied, load `procedures/intent-source.md`, run the interactive clarification flow, persist the resulting canonical intent document, and use it as the incoming source.

## Phase 0 — normalize, discover, and plan

Before ordinary discovery:

- load `procedures/remote-source-resolution.md` for supported GitHub URLs;
- load `procedures/intent-source.md` for no-source interactive mode or Markdown intent sources.

Then load:

- `procedures/source-discovery.md`
- `procedures/complexity-planning.md`.

Build the source map and complexity plan, then load only required artifact modules/procedures.

## Source eligibility

Incoming existing-artifact sources must be ordinary non-recomposition material. Existing managed artifacts are targets and may be modified as needed.

Intent sources are an exception to ordinary existing-artifact provenance rules: they describe desired future capability rather than recomposition-managed output. They are valid integration inputs, are never treated as disposable source skills, and MUST NOT be auto-deleted.

## Topic selection

Load `procedures/topic-routing.md` for semantic placement.

If `--topic` is supplied, treat it as the candidate anchor and verify full incoming semantic coverage with at most the allowed small coherent widening.

The explicit anchor is a **search boundary, not a placement preference**. Once accepted, distribute semantic fragments leaf-first within that subtree.

Without `--topic`, use global leaf-first topic discovery.

If no suitable topic exists, create a new root topic.

For interactive intent capture without `--topic`, the interview MAY record a user topic preference, but that preference does not bypass normal scope validation or leaf-first placement rules.

## Intent materialization

For an intent source:

1. preserve the user's stated goals, constraints, non-goals, examples, and interface requirements as authoritative intent evidence;
2. do not invent pre-existing contracts that do not exist;
3. decompose the intent into semantic capabilities and required runtime surfaces;
4. prefer integrating into existing valid managed skills/artifacts before creating new ones;
5. create only the minimum new skill/runtime machinery needed to satisfy the intent cleanly;
6. derive explicit policy/procedure only where needed for deterministic runtime behavior;
7. validate the resulting behavior against the intent's acceptance criteria and constraints.

If intent leaves a materially behavior-changing decision unresolved and no safe default follows from existing topic/project policy, ask a focused clarification before commit rather than guessing.

## Active artifact placement

Topic placement and physical runtime placement are separate decisions.

When commands, agents, hooks, scripts, configs, rules, adapters, or evaluations are present **or required by intent**:

- load `core/host-layout.md` and matching `artifact-types/*.md` modules;
- extract or define runtime contracts as appropriate;
- attach artifacts logically to the narrowest valid topic scope;
- preserve host-required filesystem/discovery layout;
- place shared active support at the narrowest scope covering all consumers;
- rewrite runtime-critical dependencies atomically when artifacts move/merge/rename.

For intent-created runtime surfaces, define contracts from explicit user requirements plus existing host/project conventions; do not fabricate unnecessary interfaces.

## Distribution

Semantic fragments may land in existing skills, descendant topics, new skills, and new child topics. One source may contribute to many targets.

Active artifacts MAY be retained, consolidated, wrapped, retargeted, or newly created independently from semantic fragment placement when contracts require it.

When a new topic is created, run local sibling rebalancing.

## Minimal-change objective

Preserve existing valid topic and runtime architecture by default. Change topic boundaries conservatively. Existing managed skills/support artifacts may be modified deeply where correctness requires it, but public interfaces and runtime-critical edges require explicit migration.

For intent integration, prefer extending or refining existing compatible capabilities over introducing parallel near-duplicates.

## Shared structures

Update affected glossaries, invariants, style profiles, artifact graph, supersession, provenance, and registry records.

## Mutation modules

Load for every mutation:

- `procedures/impact-analysis.md`;
- `procedures/validation.md`;
- `procedures/patching.md` unless dry-run;
- `procedures/garbage-collection.md` unless dry-run.

Load as selected by the complexity plan, source content, or affected artifacts:

- `procedures/semantic-analysis.md` when semantic instructions, knowledge, or intent material exists;
- `procedures/conflict-resolution.md` when overlapping or competing policy is detected;
- `procedures/behavior-contracts.md` and `procedures/runtime-validation.md` when active artifacts exist;
- `procedures/dependency-rewrite.md` when any active artifact is renamed, moved, split, merged, wrapped, superseded, or replaced.

## Destructive behavior

Explicit local inputs classified `disposable-source-unit` MUST be deleted automatically after successful validated commit under `procedures/source-discovery.md`. The `integrate` invocation itself authorizes deletion; require no second confirmation, deletion flag, or separate consent. Dry-run, failed validation, and uncommitted operations leave sources untouched.

Never auto-delete:

- repository/broad roots;
- user-authored intent Markdown files;
- persisted interactive intent documents;
- remote repositories (resolver-owned temporary checkouts are merely cleaned after the run).
