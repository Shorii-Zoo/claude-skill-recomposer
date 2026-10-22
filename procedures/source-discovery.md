# Source Discovery Procedure

## Purpose

Map normalized explicit sources before deep analysis so later context loading is proportional to actual complexity.

Inputs may already have been normalized by `procedures/remote-source-resolution.md` or `procedures/intent-source.md`.

## 1. Enumerate normalized sources

For each source descriptor, record:

- source kind: local existing artifact/system, resolved remote source, or intent source;
- user-facing identity and durable provenance descriptor;
- resolved local path used for analysis;
- file/directory type;
- obvious package/plugin/skill boundaries;
- files and subdirectories when applicable;
- file size, executable bit, extension, and whether content is text/binary when observable;
- manifests and discovery metadata;
- local provenance markers.

Temporary remote checkout paths are analysis-only and MUST NOT become durable lineage.

For an intent source, the canonical intent Markdown is the explicit semantic root. Do not search neighboring files merely because they are nearby.

## 2. Determine ownership

Classify files as:

- owned runtime/distribution material;
- owned validation material;
- source-repository development material;
- human documentation;
- intent specification;
- external dependency/reference;
- unknown.

A repo-root `CLAUDE.md`, `AGENTS.md`, CI config, issue template, or maintainer tooling is not automatically a reusable runtime artifact. Evidence from manifests, install scripts, explicit references, and package layout should decide.

Intent documents are evidence of desired future behavior, not existing runtime ownership.

## 3. Infer artifact kinds

For existing systems, use path conventions, frontmatter, manifests, executable metadata, references, and content shape to assign preliminary kinds from `core/artifact-model.md`.

Do not deep-read every large file merely to classify it if structural evidence is sufficient.

For intent sources, do not pretend desired runtime surfaces already exist. Record requested/implied artifact families separately as `required-by-intent` signals for complexity planning.

## 4. Detect entrypoints and active surfaces

For existing systems, identify likely:

- user/model entrypoints;
- delegated agents;
- lifecycle hooks;
- executables;
- configuration/manifests;
- adapters;
- tests/evals;
- passive references/assets.

For intent sources, identify only explicitly requested or strongly implied future surfaces, such as “I want a slash command” or “run this automatically on event X”.

## 5. Identify initial links

For existing systems, record explicit references such as:

- command → skill;
- skill → script/reference;
- agent → skill/tool;
- hook → script/agent/MCP tool;
- config → component path;
- test → target artifact;
- wrapper → canonical capability.

Do not assume a textual mention is necessarily a runtime edge; classify confidence.

For intent sources, record desired relationships separately from observed runtime edges.

## 6. Source deletion safety

Classify each source:

- `disposable-source-unit` — an installed/copied local skill or component explicitly safe to replace;
- `repository-or-broad-root` — user/source checkout or broad directory that MUST NOT be auto-deleted;
- `remote-ephemeral` — resolver-owned checkout; clean it after the run but never treat it as a deleted upstream source;
- `intent-document` — user-authored or generated requirement document; MUST NOT be auto-deleted;
- `unknown` — do not delete automatically.

Deleting source skills after recomposition/integration applies only to roots safely classified `disposable-source-unit`. For both `recompose` and `integrate`, an explicitly supplied local source classified `disposable-source-unit` MUST be deleted automatically after successful validated commit. The explicit invocation itself is deletion authorization: no second confirmation, deletion flag, separate consent, or additional authorization step is required. Record the invocation and exact owned paths as authorization. Analysis-only inputs and sources outside these explicit consumable-source semantics do not grant deletion authorization. Dry-run, failed validation, and uncommitted operations MUST leave sources untouched. Delete only after validating the replacement and capturing the source bytes and modes in the operation patch; failed validation blocks source deletion. Unknown ownership or unresolved external consumers blocks deletion. Broad repositories and non-disposable sources remain protected regardless of explicit input.

## Output

Produce a compact source map containing:

- source identities and kinds;
- artifact inventory or intent semantic root;
- ownership/scope;
- preliminary activation modes;
- observed runtime edges;
- requested runtime surfaces for intent sources;
- deletion/cleanup safety;
- unknowns.

Pass it to `procedures/complexity-planning.md`.
