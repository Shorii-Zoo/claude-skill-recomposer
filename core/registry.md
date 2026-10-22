# Registry & Provenance

## Paths

Persistent registry:

```text
<STATE_ROOT>/registry.json
```

Schema:

```text
<TOOL_ROOT>/REGISTRY.schema.json
```

The seed registry in `TOOL_ROOT` is initialization-only.

## Registry model

The registry separates logical topics from physical artifacts.

Top-level collections:

- `topics` — semantic hierarchy;
- `artifacts` — managed skills and all supporting/active artifacts;
- `dependencies` — directed graph edges between managed entities;
- `operations` — mutation/rollback history.

## Topic model

Each topic records:

- stable id and name;
- short description and full semantic scope;
- glossary path;
- effective/local style profile;
- explicit subtree invariants;
- child topics;
- `artifact_ids` logically owned by that topic.

An artifact may physically live outside the topic directory when host discovery requires it.

## Topic invariants

Topic invariants are concise cross-cutting rules that MUST remain true for the subtree.

Each invariant SHOULD have stable id, statement, and optional rationale/source.

Children inherit parent invariants unless an explicitly valid scoped specialization exists. Silent contradiction is forbidden.

## Artifact entries

Every managed artifact records at least:

- stable id;
- kind;
- name;
- path;
- short description;
- scope (`runtime`, `distribution`, `validation`, `development`, `documentation`, or `unknown`);
- primary topic id when applicable;
- activation metadata when relevant;
- host/surface when known;
- origin;
- creation and last-modifying operation ids;
- source lineage;
- provenance/fingerprint metadata where available.

Artifact kinds follow `core/artifact-model.md`.

Use file paths for fingerprinted artifacts: a skill artifact identifies its
`SKILL.md` entrypoint, not an ambiguously hashed directory. Register separately
owned policy, procedure, reference, script, and other support files as artifacts
with their own hashes and dependency edges. This lets filesystem validation and
rollback detect support-file drift without inventing a directory-hash format.

## Dependency graph

Store directed edges per `core/dependencies.md`. Runtime-critical edges must be distinguishable from informational relationships.

## Managed state and append-only ledger

`registry.json` is a mixed file, not a whole-file rollback unit. Its managed
projection is the complete parsed top-level mapping with only `operations`
removed (including unknown or invalid managed fields). `operations` is an
append-only ledger: preserve every committed entry unchanged and in order,
including the target operation, then append a successful rollback entry.
Rollback restores recorded managed prestate, not historical ledger contents.

For registry before/after fingerprints, SHA-256 the UTF-8 canonical JSON of that
projection: recursively sort object keys, preserve array order and JSON values,
use compact separators (`,` and `:`), escape non-ASCII characters (`ensure_ascii=True`), reject non-finite
numbers, and include no whitespace or trailing newline. Record this hash scope
as `registry-managed-state`; other files use `file-bytes` and exact bytes.
Never use a whole-registry byte hash as a rollback applicability check.

Retain full original registry bytes in the patch as a forensic before-image,
but restore and verify the managed projection, merging the live ledger rather
than overwriting the registry with those bytes. This also applies to failure
recovery. Even a registry initialized by an operation retains its committed
ledger after rollback; an absent managed prestate is represented as an empty
projection, not deletion of history. The resulting ledger-only mapping may be
schema-invalid; report this expected recorded managed snapshot without claiming
full validity or blocking faithful restoration solely for that reason.

`audit --fix` may repair a parseable JSON mapping with invalid managed fields.
Its patch preserves those known invalid fields in the managed before-projection;
rollback may restore them while retaining the live ledger. The existing
`operations` value MUST be a parseable list whose entries/history can be
preserved unchanged; otherwise block mutation, never reset or invent history.

## Operation history

Mutating operations record:

- operation id and mode;
- source descriptors (local paths, pinned remote lineage, and/or intent lineage);
- target topic when applicable;
- created/modified/deleted artifact ids;
- created/modified/deleted topic ids;
- source roots actually deleted;
- patch path;
- file changes with before/after hashes and metadata;
- timestamp.

Operation history entries, including `file_changes`, are metadata describing managed filesystem mutations; they exclude the operation's own patch container and operation metadata directory. The manifest and operation metadata directory contents live outside the payload. A transactional `audit --fix` repair stores its recoverable registry snapshot with that operation metadata, but the patch retains the original invalid registry bytes as a before-image; rollback and recovery use the patch, not the external snapshot.

Dry-runs do not create history entries. Read-only `check` and report-only `audit` do not create mutating entries.

## Source deletion

Explicit local sources of both `recompose` and `integrate` classified as `disposable-source-unit` MUST be deleted automatically after successful validated commit, under `procedures/source-discovery.md`. The invocation itself authorizes deletion; no additional confirmation or flag is required. Dry-run, failed validation, and uncommitted operations leave sources untouched.

Repository/broad roots and intent documents are never auto-deleted by default. Remote resolver workspaces are cleaned as ephemeral acquisition state rather than recorded as deleted sources.
