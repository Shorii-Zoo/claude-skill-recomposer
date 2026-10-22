# Runtime Behavior Contract Analysis

## Purpose

Extract what must remain compatible when transforming active artifacts.

## Contract extraction

For each active artifact, capture only relevant dimensions from `core/artifact-model.md`, including:

- invocation/public identifier;
- activation/trigger semantics;
- callers and consumers;
- arguments/input schema;
- outputs/stdout/stderr/return or response format;
- exit/error semantics;
- environment and secret references;
- permissions/tools/model/isolation;
- side effects;
- path/runtime assumptions;
- timeout/order/concurrency/lifecycle;
- host/discovery location.

## Equivalence rule

Textual overlap is insufficient to prove behavioral equivalence.

Two active artifacts MAY be consolidated only when either:

1. their contracts are compatible and every consumer can use the canonical target unchanged; or
2. a complete migration updates all consumers and preserves required compatibility through shims/adapters where appropriate.

## Interface stability

Prefer retaining externally visible names and invocation paths during recomposition unless removing/renaming them produces a clear benefit and all consumers are migrated.

User-facing entrypoints SHOULD receive compatibility shims when inexpensive and when removal would create needless breakage.

## Contract conflicts

If two artifacts share a name/surface but have incompatible contracts, do not silently merge them. Resolve through scope separation, renaming plus caller migration, explicit adapter/shim, or an unresolved blocking decision.

## Output

Produce a concise contract table and flag runtime-critical migration obligations for dependency rewrite and validation.
