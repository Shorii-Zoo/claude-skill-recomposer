# Reversible Patch Procedure

## Goal

Every committed mutating operation produces exactly one self-contained reversible patch container outside active discovery paths. This includes `rollback`: its patch captures the state before reverse application and the restored state after, and never reuses or overwrites the target operation's patch.

## Path

```text
<STATE_ROOT>/history/<operation-id>/operation.srpatch
```

## Scope

The patch payload MUST represent every managed filesystem change caused by the operation, including planned source deletion, planned garbage collection, and when applicable:

- semantic skills and references;
- commands, agents, hooks, scripts, configs, rules, adapters, tests/evals, assets;
- provenance markers;
- topic glossaries/shared references;
- registry/state-owned JSON;
- created interactive intent documents;
- file permissions/executable bits;
- symlink changes;
- deleted disposable source units.

The payload MUST exclude the operation's own patch container and operation metadata directory. The manifest may describe payload entries, but metadata runs outside the payload: repair snapshots and failure/recovery records live in `<STATE_ROOT>/history/<operation-id>/`, and `file_changes` metadata describes payload-managed mutations while excluding those locations.

A repair patch MUST retain the original invalid registry bytes as a before-image in the payload for forensic recovery. Rollback and recovery use patch before-images and MUST NOT depend on an external repair snapshot, but restore only the registry managed projection, merging the live `operations` ledger, per `core/registry.md`; never whole-file overwrite the registry. Known invalid managed fields remain part of that recorded projection.

## Failure cleanup

On failure before mutation begins, remove partial operation metadata and patch-container state created for the aborted attempt; retain them if that cleanup fails. Failures after mutation begins follow the restoration-first rule below, even if the operation has not committed.

If mutation began before failure, restore from the patch before-images and verify restored hashes/metadata. Only after successful restoration verification may partial metadata be cleaned up. Never remove the recovery patch or its metadata first. If recovery fails, retain the patch and metadata for further recovery and diagnosis.

## Representation

Use a single archive with a machine-readable manifest.

For text files other than the mixed registry, prefer reversible unified diffs plus exact-byte before/after hashes. For the registry, store before/after managed projections and their canonical digests (`registry-managed-state`) plus full bytes for forensics; merge the live ledger during restoration (`core/registry.md`). Do not apply a whole-file registry diff or use its byte hash as a rollback precondition.

For binary or metadata-sensitive artifacts, include the minimum before/after payload needed for exact reversal.

For created files, rollback deletes them after verifying the expected after hash.

For deleted files, rollback restores their prior payload and metadata.

For renamed/moved paths, represent the old/new path relationship explicitly rather than relying on similarity heuristics during rollback.

## No Git dependency

Do not require a Git repository, index, commit, or worktree. Git-like diff semantics are acceptable; Git state is not.

## Rollback

A rollback patch follows the same payload and metadata exclusion: it covers managed reverse changes and excludes its own patch container and operation metadata directory. Its failure cleanup follows the same rule: restore from before-images and verify before cleaning up metadata; never remove the recovery patch first; retain everything if recovery or cleanup fails.

Before reverse application:

1. verify operation id and manifest integrity;
2. verify current path hashes and metadata equal expected after-state (registry managed-projection digest, other files' exact bytes); any managed-projection drift blocks rollback; unrelated ledger-only appends and the shared registry path alone do not create dependency conflicts;
3. verify no later operation depends on the target state;
4. apply the patch completely in reverse;
5. verify expected managed before-state (canonical registry projection digest, other files' exact-byte hashes/metadata), preserving the live ledger;
6. validate the restored registry and runtime graph against the expected prestate; when that prestate contains known pre-existing invalidity from an `audit --fix` repair, or an absent managed prestate leaves a ledger-only mapping, report that expected schema/integrity invalidity faithfully without silently correcting it or treating faithful restoration as failed solely because of it.

After restoration validation, validate the rollback entry and proposed ledger, then atomically append it without changing existing entries. Cleanup and recovery MUST NOT truncate committed history; registry recovery merges its managed projection with the live ledger, never overwrites full bytes.

If any precondition fails, abort without partial application.
