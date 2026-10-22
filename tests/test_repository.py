"""Tests for scripts/validate_repository.py."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import validate_repository as validator  # noqa: E402

OPERATIONS = ("recompose", "integrate", "audit", "check", "rollback")


def write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")


def write_json(path: Path, data: object) -> None:
    write(path, json.dumps(data, indent=2) + "\n")


def skill_text(operations=OPERATIONS, name="skill-recomposer", hint=None):
    hint = hint if hint is not None else f"[{'|'.join(operations)}] ..."
    routes = "\n".join(f"- `{operation}` -> `operations/{operation}.md`" for operation in operations)
    return (
        "---\n"
        f"name: {name}\n"
        "description: >-\n"
        "  Route recomposition operations to their implementation modules.\n"
        "disable-model-invocation: true\n"
        f"argument-hint: \"{hint}\"\n"
        "---\n\n"
        "# Router\n\n"
        "- `core/principles.md`\n"
        f"{routes}\n"
    )


def make_valid_repository(root: Path) -> None:
    write_json(
        root / validator.SCHEMA_REL,
        json.loads((REPO_ROOT / validator.SCHEMA_REL).read_text(encoding="utf-8")),
    )
    write_json(
        root / validator.REGISTRY_REL,
        json.loads((REPO_ROOT / validator.REGISTRY_REL).read_text(encoding="utf-8")),
    )
    write_json(
        root / validator.PLUGIN_REL,
        {
            "name": "skill-recomposer",
            "version": "0.1.0",
            "description": "Test plugin manifest.",
        },
    )
    write_json(
        root / validator.MARKETPLACE_REL,
        {
            "name": "skill-recomposer",
            "description": "Test marketplace.",
            "owner": {"name": "Tester"},
            "plugins": [
                {
                    "name": "skill-recomposer",
                    "source": {"source": "github", "repo": "tester/skill-recomposer"},
                }
            ],
        },
    )
    write(root / validator.ENTRYPOINT_REL, skill_text())
    write(root / "core/principles.md", "# Principles\n")
    for operation in OPERATIONS:
        write(root / validator.OPERATIONS_REL / f"{operation}.md", f"# Operation: {operation}\n")


class RepositoryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary_directory.name)

    def tearDown(self) -> None:
        self._temporary_directory.cleanup()

    def assert_error_contains(self, errors, *fragments):
        self.assertTrue(errors, "expected validation errors")
        matching = [error for error in errors if all(fragment in error for fragment in fragments)]
        self.assertTrue(
            matching,
            f"no error containing {fragments!r}; errors were: {errors!r}",
        )


class SchemaValidationTests(RepositoryTestCase):
    def test_repository_schema_is_valid(self):
        self.assertEqual(
            validator.validate_schema_file(REPO_ROOT / validator.SCHEMA_REL),
            [],
        )

    def test_invalid_schema_is_rejected(self):
        schema_path = self.root / "REGISTRY.schema.json"
        write_json(schema_path, {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "not-a-type"})
        self.assert_error_contains(validator.validate_schema_file(schema_path), "invalid JSON Schema")

    def test_malformed_json_is_rejected(self):
        schema_path = self.root / "REGISTRY.schema.json"
        write(schema_path, "{not json")
        self.assert_error_contains(validator.validate_schema_file(schema_path), "invalid JSON")

    def test_non_object_schema_is_rejected_without_crashing(self):
        schema_path = self.root / "REGISTRY.schema.json"
        write_json(schema_path, [])
        self.assert_error_contains(
            validator.validate_schema_file(schema_path),
            "invalid JSON Schema",
        )

    def test_non_utf8_file_is_rejected_without_crashing(self):
        schema_path = self.root / "REGISTRY.schema.json"
        write(schema_path, b"\xff\xfe\x00invalid")
        self.assert_error_contains(validator.validate_schema_file(schema_path), "cannot read file")


class FrontmatterParsingTests(RepositoryTestCase):
    def test_unknown_list_map_and_block_fields_are_accepted(self):
        data, body, errors = validator.parse_frontmatter(
            "---\n"
            "name: example\n"
            "tags:\n"
            "  - one\n"
            "  - two\n"
            "metadata:\n"
            "  owner: tester\n"
            "notes: |\n"
            "  line one\n"
            "  line two\n"
            "---\n"
            "# Body\n"
        )
        self.assertEqual(errors, [])
        self.assertEqual(data["tags"], ["one", "two"])
        self.assertEqual(data["metadata"], {"owner": "tester"})
        self.assertEqual(data["notes"], "line one\nline two")
        self.assertEqual(body, "# Body")

    def test_quoted_boolean_stays_a_string(self):
        data, _, errors = validator.parse_frontmatter(
            '---\ndisable-model-invocation: "true"\n---\n'
        )
        self.assertEqual(errors, [])
        self.assertEqual(data["disable-model-invocation"], "true")
        self.assertIsNot(data["disable-model-invocation"], True)

    def test_invalid_yaml_is_reported_without_crashing(self):
        _, _, errors = validator.parse_frontmatter("---\nname: [unclosed\n---\n")
        self.assert_error_contains(errors, "invalid YAML frontmatter")

    def test_non_mapping_frontmatter_is_rejected(self):
        _, _, errors = validator.parse_frontmatter("---\n- one\n- two\n---\n")
        self.assert_error_contains(errors, "frontmatter must be a YAML mapping")


class RegistryValidationTests(RepositoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.schema_path = self.root / validator.SCHEMA_REL
        write_json(
            self.schema_path,
            json.loads((REPO_ROOT / validator.SCHEMA_REL).read_text(encoding="utf-8")),
        )
        self.registry = json.loads(
            (REPO_ROOT / validator.REGISTRY_REL).read_text(encoding="utf-8")
        )

    def test_seed_registry_is_valid(self):
        self.assertEqual(
            validator.validate_registry_file(
                REPO_ROOT / validator.REGISTRY_REL,
                REPO_ROOT / validator.SCHEMA_REL,
            ),
            [],
        )

    def test_schema_invalid_registry_is_rejected(self):
        self.registry["schema_version"] = 99
        registry_path = self.root / "registry.json"
        write_json(registry_path, self.registry)
        errors = validator.validate_registry_file(registry_path, self.schema_path)
        self.assert_error_contains(errors, "schema_version")

    def test_unknown_top_level_property_is_rejected(self):
        self.registry["unexpected"] = True
        registry_path = self.root / "registry.json"
        write_json(registry_path, self.registry)
        errors = validator.validate_registry_file(registry_path, self.schema_path)
        self.assert_error_contains(errors, "Additional properties are not allowed")

    def test_dangling_dependency_is_rejected(self):
        self.registry["dependencies"].append(
            {
                "id": "edge-1",
                "from_id": "missing-artifact",
                "to_id": "also-missing",
                "relation": "uses",
                "runtime_critical": False,
            }
        )
        registry_path = self.root / "registry.json"
        write_json(registry_path, self.registry)
        errors = validator.validate_registry_file(registry_path, self.schema_path)
        self.assert_error_contains(errors, "unknown from_id")

    def test_duplicate_dependency_ids_are_rejected(self):
        for target in ("first", "second"):
            self.registry["dependencies"].append(
                {
                    "id": "edge-1",
                    "from_id": target,
                    "to_id": target,
                    "relation": "uses",
                    "runtime_critical": False,
                }
            )
        registry_path = self.root / "registry.json"
        write_json(registry_path, self.registry)
        errors = validator.validate_registry_file(registry_path, self.schema_path)
        self.assert_error_contains(errors, "duplicate dependency id")

    def test_non_object_schema_does_not_crash_registry_validation(self):
        registry_path = self.root / "registry.json"
        write_json(registry_path, self.registry)
        write_json(self.schema_path, [])
        errors = validator.validate_registry_file(registry_path, self.schema_path)
        self.assert_error_contains(errors, "invalid JSON Schema")

    def test_malformed_registry_entries_do_not_crash_semantics(self):
        errors = validator.validate_registry_semantics(
            {
                "topics": [
                    None,
                    {"id": "topic-1", "artifact_ids": [["not", "hashable"]]},
                ],
                "artifacts": [None, {"id": "artifact-1", "primary_topic_id": ["bad"]}],
                "dependencies": [None, {"id": ["not", "hashable"]}],
                "operations": [None],
            }
        )
        self.assertIsInstance(errors, list)

    def test_topic_artifact_reference_is_checked(self):
        self.registry["topics"] = [
            {
                "type": "topic",
                "id": "topic-1",
                "name": "Topic",
                "short_description": "A topic.",
                "scope": "A topic scope.",
                "glossary_path": "topics/topic-1/glossary.md",
                "style_profile": {},
                "invariants": [],
                "artifact_ids": ["missing-artifact"],
                "items": [],
            }
        ]
        registry_path = self.root / "registry.json"
        write_json(registry_path, self.registry)
        errors = validator.validate_registry_file(registry_path, self.schema_path)
        self.assert_error_contains(errors, "references unknown artifact")

    def graph_registry(self):
        return {
            "topics": [
                {
                    "type": "topic",
                    "id": "topic-1",
                    "name": "Topic",
                    "short_description": "A topic.",
                    "scope": "Topic scope.",
                    "glossary_path": "topics/topic-1/glossary.md",
                    "style_profile": {},
                    "invariants": [],
                    "artifact_ids": ["artifact-1"],
                    "items": [],
                }
            ],
            "artifacts": [
                {
                    "id": "artifact-1",
                    "kind": "skill",
                    "name": "Skill artifact",
                    "path": "skills/artifact-1/SKILL.md",
                    "short_description": "A skill artifact.",
                    "scope": "runtime",
                    "origin": "skill-recomposition",
                    "created_by_operation_id": "op-1",
                    "last_modified_by_operation_id": "op-1",
                }
            ],
            "dependencies": [],
            "operations": [],
        }

    def test_topic_and_skill_artifact_graph_endpoints_are_accepted(self):
        registry = self.graph_registry()
        registry["dependencies"] = [
            {
                "id": "edge-1",
                "from_id": "topic-1",
                "to_id": "artifact-1",
                "relation": "uses",
                "runtime_critical": False,
            },
            {
                "id": "edge-2",
                "from_id": "artifact-1",
                "to_id": "topic-1",
                "relation": "uses",
                "runtime_critical": False,
            },
        ]
        self.assertEqual(validator.validate_registry_semantics(registry), [])

    def test_operation_ids_are_rejected_as_graph_endpoints(self):
        registry = self.graph_registry()
        registry["operations"] = [{"operation_id": "op-1"}]
        registry["dependencies"] = [
            {
                "id": "edge-1",
                "from_id": "op-1",
                "to_id": "artifact-1",
                "relation": "uses",
                "runtime_critical": False,
            }
        ]
        errors = validator.validate_registry_semantics(registry)
        self.assert_error_contains(errors, "unsupported from_id", "not operation ids")

    def test_edge_ids_are_rejected_as_graph_endpoints(self):
        registry = self.graph_registry()
        registry["dependencies"] = [
            {
                "id": "edge-1",
                "from_id": "topic-1",
                "to_id": "artifact-1",
                "relation": "uses",
                "runtime_critical": False,
            },
            {
                "id": "edge-2",
                "from_id": "edge-1",
                "to_id": "artifact-1",
                "relation": "uses",
                "runtime_critical": False,
            },
        ]
        errors = validator.validate_registry_semantics(registry)
        self.assert_error_contains(errors, "unsupported from_id", "not edge ids")

    def operation(self, operation_id, mode="recompose", file_changes=None, **overrides):
        operation = {
            "operation_id": operation_id,
            "mode": mode,
            "sources": [],
            "target_topic_id": None,
            "created_artifact_ids": [],
            "modified_artifact_ids": [],
            "deleted_artifact_ids": [],
            "created_topic_ids": [],
            "modified_topic_ids": [],
            "deleted_topic_ids": [],
            "deleted_source_paths": [],
            "patch_path": None,
            "file_changes": file_changes or [],
            "timestamp": "2026-01-01T00:00:00Z",
        }
        operation.update(overrides)
        return operation

    def file_change(self, hash_scope=None):
        change = {
            "path": "skills/example/SKILL.md",
            "change_type": "modify",
            "before_sha256": "a" * 64,
            "after_sha256": "b" * 64,
        }
        if hash_scope is not None:
            change["hash_scope"] = hash_scope
        return change

    def registry_with_operations(self, *operations):
        registry = json.loads(json.dumps(self.registry))
        registry["operations"] = list(operations)
        return registry

    def test_previous_snapshot_preserved_prefix_and_new_entries_are_accepted(self):
        previous = {"operations": [self.operation("op-1")]}
        current = {
            "operations": [self.operation("op-1"), self.operation("op-2")]
        }
        self.assertEqual(validator.validate_operation_history(current, previous), [])

    def test_previous_snapshot_truncation_is_rejected(self):
        previous = {
            "operations": [self.operation("op-1"), self.operation("op-2")]
        }
        current = {"operations": [self.operation("op-1")]}
        errors = validator.validate_operation_history(current, previous)
        self.assert_error_contains(errors, "truncated")

    def test_previous_snapshot_rewrite_is_rejected(self):
        previous = {"operations": [self.operation("op-1")]}
        current = {
            "operations": [self.operation("op-1", sources=["rewritten-source"])]
        }
        errors = validator.validate_operation_history(current, previous)
        self.assert_error_contains(errors, "differs", "unchanged and in order")

    def test_previous_snapshot_reorder_is_rejected(self):
        previous = {
            "operations": [self.operation("op-1"), self.operation("op-2")]
        }
        current = {
            "operations": [self.operation("op-2"), self.operation("op-1")]
        }
        errors = validator.validate_operation_history(current, previous)
        self.assert_error_contains(errors, "differs", "unchanged and in order")

    def test_duplicate_appended_operation_id_is_rejected(self):
        previous = {"operations": [self.operation("op-1")]}
        current = {"operations": [self.operation("op-1"), self.operation("op-1")]}
        errors = validator.validate_operation_history(current, previous)
        self.assert_error_contains(errors, "duplicate operation id")

    def test_registry_file_checks_previous_snapshot(self):
        previous_path = self.root / "previous.json"
        registry_path = self.root / "registry.json"
        write_json(
            previous_path, self.registry_with_operations(self.operation("op-1"))
        )
        write_json(
            registry_path,
            self.registry_with_operations(
                self.operation("op-1"), self.operation("op-2")
            ),
        )
        self.assertEqual(
            validator.validate_registry_file(
                registry_path, self.schema_path, previous_path
            ),
            [],
        )

        write_json(
            previous_path,
            self.registry_with_operations(
                self.operation("op-1"), self.operation("op-2")
            ),
        )
        write_json(
            registry_path, self.registry_with_operations(self.operation("op-1"))
        )
        errors = validator.validate_registry_file(
            registry_path, self.schema_path, previous_path
        )
        self.assert_error_contains(errors, "truncated")

    def test_cli_accepts_previous_registry(self):
        make_valid_repository(self.root)
        previous_path = self.root / "previous.json"
        write_json(previous_path, self.registry)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
            io.StringIO()
        ):
            status = validator.main(
                ["--root", str(self.root), "--previous-registry", str(previous_path)]
            )
        self.assertEqual(status, 0)

    def test_managed_registry_projection_excludes_operations(self):
        registry = self.registry_with_operations(self.operation("op-1"))
        projection = validator.managed_registry_projection(registry)
        self.assertNotIn("operations", projection)
        self.assertEqual(
            projection,
            {key: value for key, value in registry.items() if key != "operations"},
        )

    def test_managed_registry_digest_ignores_ledger_appends(self):
        first = self.registry_with_operations(
            self.operation("op-1", file_changes=[self.file_change()])
        )
        second = self.registry_with_operations(
            self.operation("op-1", file_changes=[self.file_change()]),
            self.operation("op-2"),
        )
        self.assertEqual(
            validator.managed_registry_digest(first),
            validator.managed_registry_digest(second),
        )

    def test_managed_registry_digest_uses_escaped_canonical_json(self):
        registry = {
            "schema_version": 2,
            "operation_name": "café",
            "operations": [self.operation("op-1")],
        }
        self.assertEqual(
            validator.managed_registry_digest(registry),
            "740ef70d1786bb307fad0cde7d3858d8ede4469f9faffcef9386db642e6058df",
        )

    def test_managed_registry_digest_rejects_nonfinite_values(self):
        registry = self.registry_with_operations()
        registry["metric"] = float("nan")
        with self.assertRaises(ValueError):
            validator.managed_registry_digest(registry)

    def test_managed_registry_digest_tracks_managed_state(self):
        first = self.registry_with_operations()
        second = self.registry_with_operations()
        second["operation_name"] = "changed"
        self.assertNotEqual(
            validator.managed_registry_digest(first),
            validator.managed_registry_digest(second),
        )

    def test_rollback_merge_restores_managed_projection_and_keeps_ledger(self):
        saved = self.registry_with_operations(self.operation("op-1"))
        saved_digest = validator.managed_registry_digest(saved)

        current = self.registry_with_operations(
            self.operation("op-1"), self.operation("op-2")
        )
        current["topics"] = [{"id": "drifted-topic"}]
        self.assertNotEqual(
            validator.managed_registry_digest(current), saved_digest
        )

        restored = validator.managed_registry_projection(saved)
        restored["operations"] = current["operations"] + [
            self.operation("op-rollback", mode="rollback")
        ]

        self.assertEqual(validator.managed_registry_digest(restored), saved_digest)
        self.assertEqual(validator.validate_operation_history(restored, saved), [])
        self.assertEqual(validator.validate_operation_history(restored, current), [])
        self.assertEqual(
            [operation["operation_id"] for operation in restored["operations"]],
            ["op-1", "op-2", "op-rollback"],
        )
        self.assertEqual(restored["topics"], saved["topics"])

    def test_file_change_hash_scope_defaults_to_file_bytes(self):
        registry_path = self.root / "registry.json"
        for scope in (None, "file-bytes", "registry-managed-state"):
            with self.subTest(scope=scope):
                write_json(
                    registry_path,
                    self.registry_with_operations(
                        self.operation(
                            "op-1", file_changes=[self.file_change(scope)]
                        )
                    ),
                )
                self.assertEqual(
                    validator.validate_registry_file(registry_path, self.schema_path),
                    [],
                )

    def test_unknown_file_change_hash_scope_is_rejected(self):
        registry_path = self.root / "registry.json"
        write_json(
            registry_path,
            self.registry_with_operations(
                self.operation(
                    "op-1", file_changes=[self.file_change("raw-bytes")]
                )
            ),
        )
        errors = validator.validate_registry_file(registry_path, self.schema_path)
        self.assert_error_contains(errors, "hash_scope")


class PluginManifestTests(RepositoryTestCase):
    def test_repository_manifests_are_valid(self):
        self.assertEqual(validator.validate_plugin_manifests(REPO_ROOT), [])

    def test_missing_version_is_rejected(self):
        make_valid_repository(self.root)
        plugin_path = self.root / validator.PLUGIN_REL
        plugin = json.loads(plugin_path.read_text(encoding="utf-8"))
        del plugin["version"]
        write_json(plugin_path, plugin)
        self.assert_error_contains(validator.validate_plugin_manifests(self.root), "version")

    def test_marketplace_without_matching_plugin_entry_is_rejected(self):
        make_valid_repository(self.root)
        marketplace_path = self.root / validator.MARKETPLACE_REL
        marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
        marketplace["plugins"][0]["name"] = "other-plugin"
        write_json(marketplace_path, marketplace)
        errors = validator.validate_plugin_manifests(self.root)
        self.assert_error_contains(errors, "no plugin entry")


class MarkdownReferenceTests(RepositoryTestCase):
    def test_repository_markdown_references_resolve(self):
        self.assertEqual(validator.validate_markdown_references(REPO_ROOT), [])

    def test_broken_backticked_module_reference_is_rejected(self):
        write(self.root / "docs/notes.md", "Load `core/missing.md` first.\n")
        errors = validator.validate_markdown_references(self.root)
        self.assert_error_contains(errors, "unresolved module reference", "core/missing.md")

    def test_broken_markdown_link_is_rejected(self):
        write(self.root / "docs/notes.md", "See [the model](core/missing.md).\n")
        errors = validator.validate_markdown_references(self.root)
        self.assert_error_contains(errors, "unresolved link target", "core/missing.md")

    def test_glob_and_external_references_are_ignored(self):
        write(
            self.root / "docs/notes.md",
            "Load `artifact-types/*.md`, `https://example.com/SKILL.md`, and `SKILL.md`.\n",
        )
        self.assertEqual(validator.validate_markdown_references(self.root), [])

    def test_references_resolve_from_tool_root_not_markdown_directory(self):
        write(self.root / "core/principles.md", "# Principles\n")
        write(self.root / "skills/example/SKILL.md", "Load `core/principles.md`.\n")
        self.assertEqual(validator.validate_markdown_references(self.root), [])

    def test_references_inside_fenced_blocks_are_ignored(self):
        write(self.root / "docs/notes.md", "```text\nexample: `core/missing.md`\n```\n")
        self.assertEqual(validator.validate_markdown_references(self.root), [])


class EntrypointTests(RepositoryTestCase):
    def test_repository_entrypoint_is_valid(self):
        self.assertEqual(validator.validate_entrypoint(REPO_ROOT), [])

    def test_missing_entrypoint_is_rejected(self):
        errors = validator.validate_entrypoint(self.root)
        self.assert_error_contains(errors, "missing canonical skill entrypoint")

    def test_entrypoint_name_must_match_directory_and_plugin(self):
        make_valid_repository(self.root)
        write(self.root / validator.ENTRYPOINT_REL, skill_text(name="other-name"))
        errors = validator.validate_entrypoint(self.root)
        self.assert_error_contains(errors, "must match skill directory")
        self.assert_error_contains(errors, "must match plugin name")

    def test_missing_description_is_rejected(self):
        make_valid_repository(self.root)
        text = skill_text().replace(
            "description: >-\n  Route recomposition operations to their implementation modules.\n",
            "",
        )
        write(self.root / validator.ENTRYPOINT_REL, text)
        self.assert_error_contains(validator.validate_entrypoint(self.root), "missing description")

    def test_missing_disable_model_invocation_is_rejected(self):
        make_valid_repository(self.root)
        text = skill_text().replace("disable-model-invocation: true\n", "")
        write(self.root / validator.ENTRYPOINT_REL, text)
        self.assert_error_contains(
            validator.validate_entrypoint(self.root),
            "missing disable-model-invocation",
        )

    def test_false_disable_model_invocation_is_rejected(self):
        make_valid_repository(self.root)
        text = skill_text().replace(
            "disable-model-invocation: true\n",
            "disable-model-invocation: false\n",
        )
        write(self.root / validator.ENTRYPOINT_REL, text)
        self.assert_error_contains(
            validator.validate_entrypoint(self.root),
            "disable-model-invocation must be true",
        )

    def test_unknown_valid_frontmatter_fields_are_accepted(self):
        make_valid_repository(self.root)
        text = skill_text().replace(
            "disable-model-invocation: true\n",
            "disable-model-invocation: true\n"
            "metadata:\n"
            "  owner: tester\n"
            "tags:\n"
            "  - one\n"
            "  - two\n"
            "notes: |\n"
            "  line one\n",
        )
        write(self.root / validator.ENTRYPOINT_REL, text)
        self.assertEqual(validator.validate_entrypoint(self.root), [])

    def test_quoted_disable_model_invocation_is_rejected(self):
        make_valid_repository(self.root)
        text = skill_text().replace(
            "disable-model-invocation: true\n",
            'disable-model-invocation: "true"\n',
        )
        write(self.root / validator.ENTRYPOINT_REL, text)
        self.assert_error_contains(
            validator.validate_entrypoint(self.root),
            "disable-model-invocation must be true",
            "not a string",
        )

    def test_non_scalar_required_fields_are_rejected_without_crashing(self):
        make_valid_repository(self.root)
        text = skill_text()
        text = text.replace("name: skill-recomposer\n", "name:\n  - skill-recomposer\n")
        text = text.replace(
            "description: >-\n  Route recomposition operations to their implementation modules.\n",
            "description:\n  - not a scalar\n",
        )
        text = text.replace(
            'argument-hint: "[recompose|integrate|audit|check|rollback] ..."\n',
            "argument-hint:\n  - recompose\n",
        )
        write(self.root / validator.ENTRYPOINT_REL, text)
        errors = validator.validate_entrypoint(self.root)
        self.assert_error_contains(errors, "name must be a non-empty string")
        self.assert_error_contains(errors, "description must be a non-empty string")
        self.assert_error_contains(errors, "argument-hint must be a non-empty string")

    def test_routing_must_reference_every_operation_module(self):
        make_valid_repository(self.root)
        write(
            self.root / validator.ENTRYPOINT_REL,
            skill_text(operations=OPERATIONS[:-1]),
        )
        errors = validator.validate_entrypoint(self.root)
        self.assert_error_contains(errors, "routing does not reference operation module", "rollback")

    def test_argument_hint_must_match_operation_modules(self):
        make_valid_repository(self.root)
        write(
            self.root / validator.ENTRYPOINT_REL,
            skill_text(hint="[recompose|integrate] ..."),
        )
        errors = validator.validate_entrypoint(self.root)
        self.assert_error_contains(errors, "argument-hint is missing operation", "audit")

    def test_unknown_operation_reference_is_rejected(self):
        make_valid_repository(self.root)
        write(
            self.root / validator.ENTRYPOINT_REL,
            skill_text() + "\n- `ghost` -> `operations/ghost.md`\n",
        )
        errors = validator.validate_entrypoint(self.root)
        self.assert_error_contains(errors, "unknown operation module", "ghost")

    def test_legacy_command_entrypoint_is_rejected(self):
        make_valid_repository(self.root)
        write(self.root / validator.LEGACY_COMMAND_REL, "# Duplicate command\n")
        self.assert_error_contains(
            validator.validate_entrypoint(self.root),
            "duplicate entrypoint",
        )


class RepositoryIntegrationTests(RepositoryTestCase):
    def test_repository_is_valid(self):
        self.assertEqual(validator.validate_repository(REPO_ROOT), [])

    def test_valid_fixture_passes_all_checks(self):
        make_valid_repository(self.root)
        self.assertEqual(validator.validate_repository(self.root), [])

    def test_validator_rejects_broken_module_reference(self):
        make_valid_repository(self.root)
        write(
            self.root / validator.ENTRYPOINT_REL,
            skill_text() + "\nSee `procedures/missing.md`.\n",
        )
        errors = validator.validate_repository(self.root)
        self.assert_error_contains(errors, "unresolved module reference", "procedures/missing.md")

    def test_validator_rejects_invalid_registry(self):
        make_valid_repository(self.root)
        registry_path = self.root / validator.REGISTRY_REL
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["schema_version"] = 1
        write_json(registry_path, registry)
        errors = validator.validate_repository(self.root)
        self.assert_error_contains(errors, "schema_version")


if __name__ == "__main__":
    unittest.main()
