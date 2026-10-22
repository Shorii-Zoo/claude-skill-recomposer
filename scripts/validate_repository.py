#!/usr/bin/env python3
"""Validate the skill-recomposer repository contracts.

Checks are intentionally structural:
- REGISTRY.schema.json is a valid Draft 2020-12 schema;
- registry.json validates against it and keeps its references coherent;
- plugin and marketplace manifests carry the required basic fields;
- every repo-relative Markdown module reference resolves against TOOL_ROOT;
- the canonical skill entrypoint exposes each operation and routes to it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

SCHEMA_REL = Path("REGISTRY.schema.json")
REGISTRY_REL = Path("registry.json")
PLUGIN_REL = Path(".claude-plugin/plugin.json")
MARKETPLACE_REL = Path(".claude-plugin/marketplace.json")
ENTRYPOINT_REL = Path("skills/skill-recomposer/SKILL.md")
LEGACY_COMMAND_REL = Path("commands/skill-recomposer.md")
OPERATIONS_REL = Path("operations")

_KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
_URL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_OPERATION_REF_RE = re.compile(r"operations/([A-Za-z0-9_.-]+)\.md")
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]]*\]\(\s*([^)\s]+)(?:\s+[^)]*)?\)")
_FENCE_RE = re.compile(r"^\s*(?:```|~~~)")


def _load_json(path: Path) -> tuple[Any | None, list[str]]:
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle), []
    except FileNotFoundError:
        return None, [f"{path}: file not found"]
    except json.JSONDecodeError as exc:
        return None, [f"{path}: invalid JSON ({exc.msg} at line {exc.lineno})"]
    except (OSError, UnicodeError) as exc:
        return None, [f"{path}: cannot read file ({exc})"]


def _json_error_location(error: Any) -> str:
    path = "/".join(str(part) for part in error.absolute_path)
    return path or "<root>"


def validate_schema_file(schema_path: Path) -> list[str]:
    """Return errors if the registry schema itself is not a valid Draft 2020-12 schema."""
    schema, errors = _load_json(schema_path)
    if schema is None:
        return errors
    if not isinstance(schema, dict):
        return [f"{schema_path}: invalid JSON Schema (schema root must be an object)"]
    try:
        Draft202012Validator.check_schema(schema)
    except (SchemaError, TypeError) as exc:
        return [f"{schema_path}: invalid JSON Schema ({exc})"]
    if "$defs" not in schema:
        return [f"{schema_path}: schema has no $defs registry definitions"]
    return []


def _walk_topics(topics: Any) -> Iterable[dict[str, Any]]:
    if not isinstance(topics, list):
        return
    for topic in topics:
        if isinstance(topic, dict):
            yield topic
            yield from _walk_topics(topic.get("items"))


def _duplicate_ids(kind: str, ids: Iterable[Any]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in ids:
        if not isinstance(value, str):
            continue
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return [f"registry: duplicate {kind} id {value!r}" for value in sorted(duplicates)]


def validate_registry_semantics(registry: Any) -> list[str]:
    """Check cross-references and ids after JSON Schema validation."""
    if not isinstance(registry, dict):
        return ["registry: top-level value must be an object"]

    topics = list(_walk_topics(registry.get("topics")))
    artifacts = registry.get("artifacts") if isinstance(registry.get("artifacts"), list) else []
    dependencies = (
        registry.get("dependencies") if isinstance(registry.get("dependencies"), list) else []
    )
    operations = registry.get("operations") if isinstance(registry.get("operations"), list) else []

    topic_ids = {topic.get("id") for topic in topics if isinstance(topic.get("id"), str)}
    artifact_ids = {
        artifact.get("id")
        for artifact in artifacts
        if isinstance(artifact, dict) and isinstance(artifact.get("id"), str)
    }
    operation_ids = {
        operation.get("operation_id")
        for operation in operations
        if isinstance(operation, dict) and isinstance(operation.get("operation_id"), str)
    }
    dependency_ids = {
        dependency.get("id")
        for dependency in dependencies
        if isinstance(dependency, dict) and isinstance(dependency.get("id"), str)
    }

    errors = []
    errors += _duplicate_ids("topic", [topic.get("id") for topic in topics])
    errors += _duplicate_ids(
        "artifact", [artifact.get("id") for artifact in artifacts if isinstance(artifact, dict)]
    )
    errors += _duplicate_ids(
        "operation",
        [operation.get("operation_id") for operation in operations if isinstance(operation, dict)],
    )
    errors += _duplicate_ids(
        "dependency",
        [dependency.get("id") for dependency in dependencies if isinstance(dependency, dict)],
    )

    for topic in topics:
        topic_artifact_ids = topic.get("artifact_ids")
        if not isinstance(topic_artifact_ids, list):
            continue
        for artifact_id in topic_artifact_ids:
            if isinstance(artifact_id, str) and artifact_id not in artifact_ids:
                errors.append(
                    f"registry: topic {topic.get('id')!r} references unknown artifact {artifact_id!r}"
                )
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        topic_id = artifact.get("primary_topic_id")
        if isinstance(topic_id, str) and topic_id not in topic_ids:
            errors.append(
                f"registry: artifact {artifact.get('id')!r} references unknown topic {topic_id!r}"
            )

    for dependency in dependencies:
        if not isinstance(dependency, dict):
            continue
        for field in ("from_id", "to_id"):
            target = dependency.get(field)
            if not isinstance(target, str):
                continue
            if target in artifact_ids or target in topic_ids:
                continue
            if target in operation_ids:
                entity = "operation"
            elif target in dependency_ids:
                entity = "edge"
            else:
                errors.append(
                    f"registry: dependency {dependency.get('id')!r} has unknown {field} {target!r}"
                )
                continue
            errors.append(
                f"registry: dependency {dependency.get('id')!r} has unsupported {field} {target!r}; "
                f"graph endpoints must be topic or artifact ids, not {entity} ids"
            )
    return errors


def managed_registry_projection(registry: Any) -> dict[str, Any]:
    """Return managed registry state: all top-level fields except the operation ledger."""
    if not isinstance(registry, dict):
        raise TypeError("registry must be a JSON object")
    return {key: value for key, value in registry.items() if key != "operations"}


def managed_registry_digest(registry: Any) -> str:
    """Return the deterministic SHA-256 digest of the managed registry projection."""
    canonical = json.dumps(
        managed_registry_projection(registry),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_operation_history(
    registry: Any,
    previous: Any,
    registry_label: str = "registry",
    previous_label: str = "previous registry",
) -> list[str]:
    """Check that previous operations remain an exact prefix of current operations.

    Comparing two snapshots detects truncation, rewriting, and reordering
    relative to the supplied previous snapshot. It does not prove append-only
    history for a ledger observed in isolation, and new unique entries are
    permitted.
    """
    if not isinstance(previous, dict):
        return [f"{previous_label}: previous registry must be a JSON object"]
    current_operations = registry.get("operations") if isinstance(registry, dict) else None
    previous_operations = previous.get("operations")
    if not isinstance(previous_operations, list):
        return [f"{previous_label}: operations must be a list"]
    if not isinstance(current_operations, list):
        return [f"{registry_label}: operations must be a list"]

    errors = []
    for index, expected in enumerate(previous_operations):
        if index >= len(current_operations):
            errors.append(
                f"{registry_label}: operations ledger truncated; previous operation at index "
                f"{index} is missing"
            )
            break
        if current_operations[index] != expected:
            errors.append(
                f"{registry_label}: operations[{index}] differs from {previous_label}; "
                "existing operations must remain unchanged and in order"
            )
            break
    if errors:
        return errors

    seen: set[str] = set()
    for operation in current_operations:
        if not isinstance(operation, dict):
            continue
        operation_id = operation.get("operation_id")
        if not isinstance(operation_id, str):
            continue
        if operation_id in seen:
            errors.append(
                f"{registry_label}: duplicate operation id {operation_id!r}; "
                "appended operations must be unique"
            )
            continue
        seen.add(operation_id)
    return errors


def validate_registry_file(
    registry_path: Path,
    schema_path: Path,
    previous_registry_path: Path | None = None,
) -> list[str]:
    registry, errors = _load_json(registry_path)
    if registry is None:
        return errors
    schema, schema_errors = _load_json(schema_path)
    if schema is None:
        return schema_errors
    if not isinstance(schema, dict):
        return [f"{schema_path}: invalid JSON Schema (schema root must be an object)"]
    try:
        validator = Draft202012Validator(schema)
    except (SchemaError, TypeError) as exc:
        return [f"{schema_path}: invalid JSON Schema ({exc})"]

    errors = []
    for error in sorted(validator.iter_errors(registry), key=lambda item: list(item.absolute_path)):
        errors.append(f"{registry_path}:{_json_error_location(error)}: {error.message}")
    if not errors:
        errors.extend(validate_registry_semantics(registry))

    if previous_registry_path is not None:
        previous, previous_errors = _load_json(previous_registry_path)
        errors.extend(previous_errors)
        if not previous_errors:
            if not isinstance(previous, dict):
                errors.append(
                    f"{previous_registry_path}: previous registry must be a JSON object"
                )
            elif not errors:
                errors.extend(
                    validate_operation_history(
                        registry,
                        previous,
                        str(registry_path),
                        str(previous_registry_path),
                    )
                )
    return errors


def validate_plugin_manifests(root: Path) -> list[str]:
    errors: list[str] = []
    plugin_path = root / PLUGIN_REL
    marketplace_path = root / MARKETPLACE_REL

    plugin, plugin_errors = _load_json(plugin_path)
    errors.extend(plugin_errors)
    plugin_name = None
    if isinstance(plugin, dict):
        plugin_name = plugin.get("name")
        if not isinstance(plugin_name, str) or not plugin_name:
            errors.append(f"{plugin_path}: missing non-empty name")
        elif not _KEBAB_RE.fullmatch(plugin_name):
            errors.append(f"{plugin_path}: name must be kebab-case")
        version = plugin.get("version")
        if not isinstance(version, str) or not version:
            errors.append(f"{plugin_path}: missing non-empty version")
        elif not _SEMVER_RE.fullmatch(version):
            errors.append(f"{plugin_path}: version must be semver")
        description = plugin.get("description")
        if not isinstance(description, str) or not description.strip():
            errors.append(f"{plugin_path}: missing non-empty description")
    elif plugin is not None:
        errors.append(f"{plugin_path}: manifest must be a JSON object")

    marketplace, marketplace_errors = _load_json(marketplace_path)
    errors.extend(marketplace_errors)
    if isinstance(marketplace, dict):
        if not isinstance(marketplace.get("name"), str) or not marketplace.get("name"):
            errors.append(f"{marketplace_path}: missing non-empty name")
        owner = marketplace.get("owner")
        if not isinstance(owner, dict) or not isinstance(owner.get("name"), str) or not owner.get(
            "name"
        ):
            errors.append(f"{marketplace_path}: missing owner.name")
        plugins = marketplace.get("plugins")
        if not isinstance(plugins, list) or not plugins:
            errors.append(f"{marketplace_path}: plugins must be a non-empty list")
        else:
            entry_names = []
            for entry in plugins:
                if not isinstance(entry, dict):
                    errors.append(f"{marketplace_path}: each plugin entry must be an object")
                    continue
                entry_name = entry.get("name")
                entry_names.append(entry_name)
                if not isinstance(entry_name, str) or not entry_name:
                    errors.append(f"{marketplace_path}: plugin entry missing name")
                source = entry.get("source")
                if not source:
                    errors.append(f"{marketplace_path}: plugin entry {entry_name!r} missing source")
            if plugin_name and plugin_name not in entry_names:
                errors.append(
                    f"{marketplace_path}: no plugin entry for plugin name {plugin_name!r}"
                )
    elif marketplace is not None:
        errors.append(f"{marketplace_path}: manifest must be a JSON object")
    return errors


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str, list[str]]:
    """Parse skill frontmatter as YAML, accepting arbitrary valid fields."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text, ["missing YAML frontmatter opening delimiter"]

    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    if end is None:
        return {}, text, ["unterminated YAML frontmatter"]

    body = "\n".join(lines[end + 1 :])
    try:
        data = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as exc:
        return {}, body, [f"invalid YAML frontmatter ({exc})"]
    if data is None:
        return {}, body, []
    if not isinstance(data, dict):
        return {}, body, ["frontmatter must be a YAML mapping"]
    return data, body, []


def _operation_modules(root: Path) -> set[str]:
    operations_dir = root / OPERATIONS_REL
    if not operations_dir.is_dir():
        return set()
    return {path.stem for path in operations_dir.glob("*.md")}


def _hint_subcommands(hint: str) -> list[str] | None:
    match = re.search(r"\[([^\]]*)\]", hint)
    if not match:
        return None
    return [part.strip().strip("`") for part in match.group(1).split("|") if part.strip()]


def _body_operation_refs(body: str) -> set[str]:
    return set(_OPERATION_REF_RE.findall(body))


def validate_entrypoint(root: Path) -> list[str]:
    """Validate the canonical skill entrypoint and its routing table."""
    path = root / ENTRYPOINT_REL
    if not path.is_file():
        return [f"{ENTRYPOINT_REL}: missing canonical skill entrypoint"]

    errors: list[str] = []
    legacy = root / LEGACY_COMMAND_REL
    if legacy.exists():
        errors.append(
            f"{LEGACY_COMMAND_REL}: duplicate entrypoint; the canonical entrypoint is {ENTRYPOINT_REL}"
        )

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return errors + [f"{ENTRYPOINT_REL}: cannot read file ({exc})"]

    data, body, frontmatter_errors = parse_frontmatter(text)
    errors.extend(f"{ENTRYPOINT_REL}: {message}" for message in frontmatter_errors)

    name_value = data.get("name")
    name = name_value.strip() if isinstance(name_value, str) else ""
    if "name" not in data:
        errors.append(f"{ENTRYPOINT_REL}: frontmatter missing name")
    elif not name:
        errors.append(f"{ENTRYPOINT_REL}: name must be a non-empty string")
    else:
        if not _KEBAB_RE.fullmatch(name):
            errors.append(f"{ENTRYPOINT_REL}: name must be kebab-case")
        if name != path.parent.name:
            errors.append(
                f"{ENTRYPOINT_REL}: name {name!r} must match skill directory {path.parent.name!r}"
            )
        plugin, plugin_errors = _load_json(root / PLUGIN_REL)
        if isinstance(plugin, dict) and isinstance(plugin.get("name"), str):
            if plugin["name"] != name:
                errors.append(
                    f"{ENTRYPOINT_REL}: name {name!r} must match plugin name {plugin['name']!r}"
                )

    description_value = data.get("description")
    description = description_value.strip() if isinstance(description_value, str) else ""
    if "description" not in data:
        errors.append(f"{ENTRYPOINT_REL}: frontmatter missing description")
    elif not description:
        errors.append(f"{ENTRYPOINT_REL}: description must be a non-empty string")
    elif len(description) > 1024:
        errors.append(f"{ENTRYPOINT_REL}: description exceeds 1024 characters")

    if "disable-model-invocation" not in data:
        errors.append(f"{ENTRYPOINT_REL}: frontmatter missing disable-model-invocation: true")
    elif data["disable-model-invocation"] is not True:
        errors.append(
            f"{ENTRYPOINT_REL}: disable-model-invocation must be true as a boolean, not a string"
        )

    hint_value = data.get("argument-hint")
    hint = hint_value.strip() if isinstance(hint_value, str) else ""
    if "argument-hint" not in data:
        errors.append(f"{ENTRYPOINT_REL}: frontmatter missing argument-hint")
    elif not hint:
        errors.append(f"{ENTRYPOINT_REL}: argument-hint must be a non-empty string")
    else:
        subcommands = _hint_subcommands(hint)
        if subcommands is None:
            errors.append(f"{ENTRYPOINT_REL}: argument-hint must contain a [a|b] subcommand list")
        else:
            if len(subcommands) != len(set(subcommands)):
                errors.append(f"{ENTRYPOINT_REL}: argument-hint repeats a subcommand")
            modules = _operation_modules(root)
            missing = sorted(modules - set(subcommands))
            extra = sorted(set(subcommands) - modules)
            if missing:
                errors.append(
                    f"{ENTRYPOINT_REL}: argument-hint is missing operation(s) {', '.join(missing)}"
                )
            if extra:
                errors.append(
                    f"{ENTRYPOINT_REL}: argument-hint names unknown operation(s) {', '.join(extra)}"
                )

    modules = _operation_modules(root)
    referenced = _body_operation_refs(body)
    missing = sorted(modules - referenced)
    unknown = sorted(referenced - modules)
    if missing:
        errors.append(
            f"{ENTRYPOINT_REL}: routing does not reference operation module(s) {', '.join(missing)}"
        )
    if unknown:
        errors.append(
            f"{ENTRYPOINT_REL}: routing references unknown operation module(s) {', '.join(unknown)}"
        )
    return errors


def _strip_fenced_blocks(text: str) -> list[str]:
    stripped = []
    in_fence = False
    for line in text.splitlines():
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            stripped.append("")
        elif in_fence:
            stripped.append("")
        else:
            stripped.append(line)
    return stripped


def _local_module_ref(raw: str) -> str | None:
    """Return a TOOL_ROOT-relative .md module path, or None for non-module references."""
    ref = raw.strip()
    if not ref or any(char in ref for char in "*?{}<>"):
        return None
    if ref.startswith(("./", "../", "/", "~", "#", ".")):
        return None
    if _URL_RE.match(ref):
        return None
    ref = ref.split("#", 1)[0].split("?", 1)[0].rstrip(".,;:")
    if not ref.lower().endswith(".md") or "/" not in ref:
        return None
    parts = ref.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return None
    if re.fullmatch(r"[A-Za-z0-9-]+\.[A-Za-z]{2,}", parts[0]):
        return None
    return ref


def validate_markdown_references(root: Path) -> list[str]:
    """Check every repo-relative .md reference against TOOL_ROOT."""
    errors: list[str] = []
    for markdown_path in sorted(root.rglob("*.md")):
        relative_path = markdown_path.relative_to(root)
        if any(part.startswith(".") for part in relative_path.parts):
            continue
        try:
            text = markdown_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"{relative_path}: cannot read file ({exc})")
            continue
        for line_number, line in enumerate(_strip_fenced_blocks(text), start=1):
            for match in _INLINE_CODE_RE.finditer(line):
                ref = _local_module_ref(match.group(1))
                if ref and not (root / ref).is_file():
                    errors.append(
                        f"{relative_path}:{line_number}: unresolved module reference `{ref}`"
                    )
            for match in _MARKDOWN_LINK_RE.finditer(line):
                ref = _local_module_ref(match.group(1))
                if ref and not (root / ref).is_file():
                    errors.append(
                        f"{relative_path}:{line_number}: unresolved link target `{ref}`"
                    )
    return errors


def validate_repository(
    root: Path, previous_registry_path: Path | None = None
) -> list[str]:
    schema_path = root / SCHEMA_REL
    errors: list[str] = []
    errors.extend(validate_schema_file(schema_path))
    errors.extend(
        validate_registry_file(root / REGISTRY_REL, schema_path, previous_registry_path)
    )
    errors.extend(validate_plugin_manifests(root))
    errors.extend(validate_markdown_references(root))
    errors.extend(validate_entrypoint(root))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="TOOL_ROOT to validate (default: repository containing this script)",
    )
    parser.add_argument(
        "--previous-registry",
        type=Path,
        help="prior registry snapshot whose operations must remain an exact prefix",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()

    errors = validate_repository(root, args.previous_registry)
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        print(f"{len(errors)} repository problem(s) found.", file=sys.stderr)
        return 1
    print(f"Repository validation passed for {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
