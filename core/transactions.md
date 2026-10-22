# Transaction, Dry-Run, Patch, and Destructive Safety

## Dry-run

Mutating operations MUST support `--dry-run`.

A dry-run performs discovery, analysis, planning, impact analysis, and validation planning but MUST NOT:

- write or modify managed artifacts;
- create `STATE_ROOT` or initialize/update the registry;
- update provenance/fingerprints;
- create/update glossaries;
- persist interactive intent documents;
- delete sources;
- create operation patches, including rollback patches;
- run destructive garbage collection.

It SHOULD report the complete proposed change set, runtime migrations, likely impact, and source-deletion eligibility.

## Transactional mutation

Stage the complete target state conceptually or in a temporary non-discoverable workspace before destructive changes.

Commit order:

1. validate source eligibility and deletion scope;
2. discover artifact graph and contracts;
3. perform semantic, runtime, and impact analysis;
4. compute the complete proposed filesystem, registry, source-deletion, garbage-collection, and intent-document changes;
5. validate candidate semantic architecture;
6. validate candidate runtime graph when active artifacts exist;
7. create one reversible operation patch container covering every managed filesystem change computed in step 4, excluding the operation's own patch container and operation metadata directory; operation metadata directory contents stay outside the payload;
8. apply target changes;
9. update registry/provenance/dependency data;
10. revalidate committed state;
11. delete only source roots explicitly marked disposable: every explicitly supplied local `recompose` or `integrate` source so classified MUST be deleted automatically under `procedures/source-discovery.md`, without additional authorization;
12. run safe garbage collection;
13. validate once more;
14. validate the candidate committed operation entry and full proposed ledger, then atomically persist its append to live `registry.operations` only after all validation succeeds; preserve the existing ledger prefix unchanged. A persistence failure must never partially write or truncate history.

Steps 11-12 are part of the planned change set: their effects MUST already be represented in the patch created at step 7. If an unplanned change becomes necessary, abort, recompute the change set, and create a replacement patch before continuing.

If failure occurs before step 8, do not delete source roots; remove operation-owned state created for the aborted attempt — partial patch-container state, operation metadata, snapshots, and any generated interactive intent document — and leave the managed library and registry untouched. If that cleanup fails, retain the partial metadata and snapshot for recovery and diagnosis.

If failure occurs after mutation begins, reverse-apply the operation patch to restore the pre-operation filesystem and registry state using the patch's before-images, not any external snapshot; restore the registry managed projection merged with the live ledger, and verify projection digests plus other files' exact-byte hashes/metadata. Never truncate committed ledger entries, even during cleanup. Only after restoration verifies successfully may partial metadata be cleaned up. Never remove the recovery patch or its metadata before that verification. If recovery fails, retain the patch and metadata for further recovery and diagnosis, report the exact unrecovered paths and registry state, and stop further mutation. Record the operation as failed rather than committed; record the failure diagnostic outside the payload, or report it inline when operation metadata was cleaned up. Do not delete source roots except as reversed by that patch.

## Single-file rollback package

Rollback history MUST live outside active skill/plugin discovery paths.

Store one patch container per operation:

```text
<STATE_ROOT>/history/<operation-id>/operation.srpatch
```

A `rollback` operation also creates its own patch container before reverse application. It captures the current post-target-operation state as before and the restored state as after, and MUST NOT overwrite the target operation's patch.

The patch payload is independent of Git and MUST capture every reversible managed filesystem change, including:

- text diffs;
- binary creations/modifications/deletions when present;
- file mode changes such as executable bits;
- symlink targets when present;
- created/deleted directories when material;
- registry/provenance changes;
- source deletion for disposable sources.

## Patch container

`operation.srpatch` SHOULD be a single archive containing a manifest plus payloads. The exact internal representation may evolve, but it MUST be self-contained and reversible.

The operation's own patch container and operation metadata directory are not payload entries. The manifest describes payload entries and operation metadata, but metadata itself — including repair snapshots and failure/recovery records — is stored outside the payload in `<STATE_ROOT>/history/<operation-id>/`; `file_changes` metadata describes payload-managed mutations and excludes those locations.

A repair patch MUST retain the original invalid registry bytes as a before-image in the payload for forensics. Rollback and recovery use patch before-images and MUST NOT depend on an external repair snapshot; registry restoration uses the managed projection merged with the live ledger, never whole-file overwrite, per `core/registry.md`.

A recommended layout is:

```text
manifest.json
text/*.diff
before/*
after/*
```

Use unified text diffs where safe. Store binary or metadata-sensitive before/after payloads only when required.

## Hashes and metadata

Registry operation metadata MUST record before/after SHA-256 hashes and relevant file metadata for every changed artifact. Other files use exact bytes (`file-bytes`); the registry uses canonical managed-projection digests (`registry-managed-state`) excluding top-level `operations`, per `core/registry.md`. Full registry bytes are forensic payload only, not rollback hashes or restoration units.

Use `null` when a path did not exist in the corresponding state.

## Rollback safety

Never reverse blindly. Verify current paths/hashes/modes/symlink state match expected post-operation preconditions.

If current state diverged, stop instead of overwriting newer work.

A rollback restores recorded managed prestate, excluding the append-only ledger: exact bytes for other files, canonical managed projection for the registry (`core/registry.md`). Merge the live ledger and append the validated rollback entry after successful restoration validation; never truncate committed entries. If the target operation repaired a previously invalid registry, the restored prestate may carry those known pre-existing defects; report them faithfully rather than silently repairing the restored snapshot or treating faithful restoration as failed solely because of them.

Later operations that depend on the target operation, or that overlap its managed changes or affected artifact/topic ids, must be resolved safely first. The shared registry path alone is not a conflict for unrelated ledger-only appends. Any managed-projection drift blocks rollback, including otherwise unrelated managed edits; never erase newer managed state.

## Ephemeral acquisition and intent inputs

Resolver-owned GitHub checkouts are ephemeral analysis workspaces, not user-owned source mutations. They MUST be cleaned on success, dry-run, cancellation, or failure and MUST NOT be stored as rollback deletions.

User-authored intent documents are input evidence: they MUST NOT be modified, deleted, or included in the operation patch. Newly generated interactive intent documents are operation-owned state: their creation MUST be recorded in history and included in the operation patch so rollback removes them.
