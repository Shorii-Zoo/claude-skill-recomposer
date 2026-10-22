# Dependency & Reference Rewrite Procedure

## Trigger

Use when any artifact is renamed, moved, split, merged, wrapped, superseded, or replaced.

## 1. Compute reverse dependency closure

Using the registry graph plus discovered explicit references, identify every consumer that may require change.

Prioritize runtime-critical edges before semantic links.

## 2. Rewrite by contract

Update references according to relation type:

- invocations and delegation names;
- executable/script paths;
- hook handler targets;
- manifest component paths;
- skill/reference links;
- agent skill/tool declarations;
- adapter canonical targets;
- tests/evals/fixtures;
- docs only when they describe runtime use.

Do not globally search/replace identifiers without confirming semantic identity.

## 3. Compatibility shims

When retaining an old public entrypoint is useful, create the smallest shim that delegates to the canonical target. Mark it as compatibility surface and link it to the canonical target with a `wraps` edge; use `supersedes` only from the canonical artifact to a retired one.

A shim MUST NOT duplicate the full underlying implementation.

## 4. Validate no stale critical references

Before destructive commit, every runtime-critical old path/name MUST either:

- be migrated;
- remain intentionally valid;
- be served by a compatibility shim; or
- block the operation.
