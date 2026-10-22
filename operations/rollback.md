# Operation: rollback

## Invocation

```text
/skill-recomposer rollback <operation-id> [--dry-run]
```

## Load

Load the core kernel plus:

- `procedures/patching.md`;
- `procedures/validation.md`;
- `procedures/impact-analysis.md` when later operations may depend on the target operation;
- `procedures/runtime-validation.md` when the patch affects active artifacts.

## Preconditions

Locate `<STATE_ROOT>/history/<operation-id>/operation.srpatch` and its operation record.

Verify current affected paths match expected post-operation hashes and metadata: exact bytes for other files; the canonical managed-projection digest for `registry.json`, excluding top-level `operations`, per `core/registry.md`. Preserve the live ledger unchanged.

Inspect later operations for dependencies on entities or contracts introduced/modified by the target operation. Refuse unsafe out-of-order rollback. A later operation also depends on the target when its recorded file-change paths overlap the target's changed paths, or when its created/modified/deleted artifact or topic ids overlap the target's affected ids. The shared registry path alone is not overlap when only unrelated ledger entries were appended. Any managed-projection drift from the target's expected after-state blocks rollback, even for otherwise unrelated managed edits; restoring the whole projection must not erase them.

## Behavior

Dry-run reports applicability, the exact reverse change set, the proposed rollback operation record, and the rollback patch that would be created; it writes nothing.

Non-dry-run first creates its own reversible patch container at `<STATE_ROOT>/history/<rollback-operation-id>/operation.srpatch`, covering the managed reverse changes but excluding its own patch container and operation metadata directory; the new operation record is metadata outside the payload. It then reverse-applies the target patch container, restoring source units and prior managed state encoded by the operation, and verifies the recorded managed prestate: canonical registry projection digest merged with the unchanged live ledger, exact-byte hashes and metadata for other files. Never replace the registry from its forensic full-byte before-image.

For a rollback of `audit --fix`, the restored managed projection MAY contain the original invalid managed fields by design, while the live ledger survives unchanged. Report known pre-existing schema or integrity errors faithfully without pretending the registry is valid, silently altering the restored snapshot, or blocking faithful restoration solely because of those pre-existing defects. The current pre-rollback state must still satisfy the existing valid-state precondition.

After restoration validation, validate a new operation entry with mode `rollback`, `patch_path` pointing to the rollback patch, and `sources` naming the rolled-back operation id, plus the full proposed ledger. Atomically append it to the live ledger without changing any prior committed entry. Persistence or cleanup must never truncate history. An originally absent managed prestate yields a ledger-only mapping; report its expected schema invalidity as recorded, just like known invalid managed fields from repair.

Never partially rollback when preconditions fail. On failure before mutation begins, remove partial rollback metadata and container state created for the attempt; retain them if cleanup fails. If reverse application fails after mutation begins, restore the pre-rollback managed state from the rollback patch's before-images, merging the live ledger, and verify projection digests plus other files' exact-byte hashes/metadata before reporting failure. Never remove or rewrite committed ledger entries. Only after successful restoration verification may partial metadata be cleaned up; never remove the recovery patch or its metadata first, and retain them if recovery fails.
