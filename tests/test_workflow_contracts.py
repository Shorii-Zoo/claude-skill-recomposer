"""Specification-consistency checks, not transaction-engine execution tests."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def section(path, heading):
    """Extract a Markdown section, including lower-level subsections."""
    text = (ROOT / path).read_text(encoding="utf-8")
    match = re.search(rf"^(#+) {re.escape(heading)}\s*$", text, re.MULTILINE)
    if match is None:
        raise AssertionError(f"Missing section {heading!r} in {path}")
    following = text[match.end():]
    end = re.search(rf"^#{{1,{len(match[1])}}} ", following, re.MULTILINE)
    return " ".join(following[:end.start() if end else None].split())


class WorkflowContractSpecTests(unittest.TestCase):
    """Guard essential documented semantics without simulating a runtime."""

    def test_audit_repair_accepts_parseable_invalid_state(self):
        text = section("operations/audit.md", "--fix")
        self.assertRegex(text, r"parseable registry.*invalid.*MAY.*repaired transactionally")
        self.assertRegex(text, r"original invalid registry bytes.*before-image")
        validation = section("procedures/validation.md", "Semantic integrity")
        self.assertIn("registry against schema", validation)
        transaction = section("core/transactions.md", "Transactional mutation")
        self.assertRegex(transaction, r"validate candidate semantic architecture.*create one reversible operation patch")

    def test_unrecoverable_registry_blocks_mutation(self):
        text = section("operations/audit.md", "--fix")
        self.assertRegex(text, r"unreadable or cannot be recovered.*stop without mutation")

    def test_patch_payload_excludes_own_metadata(self):
        scope = section("procedures/patching.md", "Scope")
        self.assertRegex(scope, r"exclude.*own patch container and operation metadata directory")
        self.assertRegex(scope, r"outside the payload.*repair snapshots")
        self.assertIn("file_changes", scope)
        container = section("core/transactions.md", "Patch container")
        self.assertRegex(container, r"file_changes.*excludes those locations")
        self.assertRegex(container, r"invalid registry bytes.*before-image in the payload")
        self.assertRegex(container, r"MUST NOT depend on an external repair snapshot")
        rollback = section("procedures/patching.md", "Rollback")
        self.assertRegex(rollback, r"rollback patch.*excludes.*own patch container and operation metadata directory")

    def test_failure_cleanup_and_recovery_evidence(self):
        cleanup = section("procedures/patching.md", "Failure cleanup")
        self.assertRegex(cleanup, r"before (?:commit|mutation begins), remove.*partial operation metadata.*patch-container state")
        self.assertRegex(cleanup, r"retain them if that cleanup fails")
        transaction = section("core/transactions.md", "Transactional mutation")
        self.assertRegex(transaction, r"before step 8.*remove.*partial patch-container state.*operation metadata")
        self.assertRegex(transaction, r"restore.*pre-operation.*before-images, not any external snapshot")
        self.assertRegex(transaction, r"Never remove the recovery patch.*before that verification")
        self.assertRegex(transaction, r"recovery fails, retain.*patch and metadata")

    def test_explicit_disposable_inputs_are_consumed_by_both_operations(self):
        discovery = section("procedures/source-discovery.md", "6. Source deletion safety")
        for operation in ("recompose", "integrate"):
            with self.subTest(operation=operation):
                self.assertIn(f"`{operation}`", discovery)
                self.assertIn("explicitly supplied local source classified `disposable-source-unit`", discovery)
                self.assertIn("MUST be deleted automatically after successful validated commit", discovery)
                self.assertIn("explicit invocation itself is deletion authorization", discovery)
                self.assertIn("no second confirmation, deletion flag, separate consent", discovery)
                transaction = section("core/transactions.md", "Transactional mutation")
                self.assertIn(f"`{operation}`", transaction)
                self.assertIn("MUST be deleted automatically", transaction)

    def test_failed_uncommitted_and_dry_run_preserve_both_source_kinds(self):
        discovery = section("procedures/source-discovery.md", "6. Source deletion safety")
        self.assertIn("Dry-run, failed validation, and uncommitted operations MUST leave sources untouched", discovery)
        dry_run = section("core/transactions.md", "Dry-run")
        self.assertIn("MUST NOT", dry_run)
        self.assertIn("delete sources", dry_run)
        self.assertIn("Broad repositories and non-disposable sources remain protected", discovery)

    def test_rollback_preserves_append_only_ledger(self):
        registry = section("core/registry.md", "Managed state and append-only ledger")
        self.assertIn("append-only ledger", registry)
        self.assertIn("preserve every committed entry unchanged and in order", registry)
        self.assertIn("append a successful rollback entry", registry)
        self.assertIn("registry-managed-state", registry)
        self.assertIn("merging the live ledger", registry)
        rollback = section("operations/rollback.md", "Behavior")
        self.assertIn("ledger", rollback)
        self.assertIn("managed", rollback)

    def test_existing_source_deletion_safeguards(self):
        source = section("procedures/source-discovery.md", "6. Source deletion safety")
        self.assertRegex(source, r"repository-or-broad-root.*MUST NOT be auto-deleted")
        self.assertRegex(source, r"Unknown ownership or unresolved external consumers blocks deletion")
        transaction = section("core/transactions.md", "Transactional mutation")
        self.assertRegex(transaction, r"failure occurs before step 8, do not delete source roots")
        self.assertRegex(transaction, r"10\. revalidate committed state; 11\. delete only source roots")


if __name__ == "__main__":
    unittest.main()
