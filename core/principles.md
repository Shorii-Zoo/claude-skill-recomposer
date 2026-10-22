# Core Principles

## Operation name

The operation is **Skill Recomposition**. Use **recomposition** as the short name.

## Explicit invocation only

Recomposition MUST never activate implicitly. Only the `skill-recomposer` entrypoint may invoke it; the entrypoint MUST disable model invocation.

## Source scope

Only explicitly supplied inputs are source roots. An input may be a local path, a supported GitHub URL resolved by `procedures/remote-source-resolution.md`, or (for `integrate`) a user intent document produced/provided under `procedures/intent-source.md`.

Do not silently import nearby installed skills, plugins, agents, commands, references, sibling repository content outside an explicit remote subpath, or neighboring files around an intent document merely because they appear related.

Owned files reachable from an explicit existing-artifact source MAY be analyzed when `procedures/source-discovery.md` establishes that they are part of that source's runtime or distribution unit. Intent sources describe desired future behavior and do not imply ownership of nearby artifacts.

## Skill-system model

A source may be pure knowledge, a single workflow skill, or a behavior-rich system containing commands, agents, hooks, scripts, rules, configuration, adapters, evaluations, templates, and other resources.

Do not reduce active artifacts to prose. Preserve both:

1. semantic intent; and
2. operational contracts and graph relationships.

## Non-reentry

Any artifact produced or managed by recomposition MUST NOT be accepted as ordinary existing-artifact source material to `recompose` or `integrate`. Canonical intent documents stored under `<STATE_ROOT>/intents/` are requirement inputs rather than managed skill-system outputs and remain valid `integrate` sources.

Managed artifacts MAY be modified as targets during `integrate`, `audit --fix`, rollback, or maintenance.

Reject the operation before semantic or destructive work if registry provenance, local provenance markers, or stored output fingerprints identify any supplied source as recomposition-managed. If provenance is materially ambiguous, fail closed.

## Semantic boundaries over source boundaries

Source files and directories are evidence, not authoritative target architecture. Recomposition may split, merge, move, canonicalize, wrap, supersede, or retarget material when contracts remain valid.

The target is neither maximal merging nor maximal splitting. Prefer maximum semantic and behavioral preservation with minimum routing ambiguity, unnecessary context, and duplicated runtime machinery.

## Knowledge and execution

Preserve conceptual plurality in Knowledge Space. Eliminate unresolved operational ambiguity in Execution Policy.

A runtime policy MUST NOT leave simultaneously applicable incompatible instructions unresolved unless explicit precedence, conditions, defaults, overrides, or a user/project choice determine what wins.

## Contract preservation

Behavioral equivalence matters more than textual similarity for active artifacts.

Do not merge, rename, move, or delete an entrypoint, executable, handler, agent, or configuration key merely because its text overlaps another artifact. First identify callers, triggers, inputs, outputs, side effects, lifecycle, permissions, path assumptions, and compatibility obligations.

## Minimal-change rule for integration

`integrate` MUST preserve valid existing topic and runtime architecture unless semantic correctness, routing clarity, dependency integrity, contract preservation, or a materially better containment relation requires restructuring.

Existing managed skills and support artifacts MAY be modified deeply when necessary. Existing public interfaces and topic boundaries should change more conservatively.

## Safe uncertainty

When an artifact type, schema, lifecycle, or contract cannot be understood confidently, preserve it and report the uncertainty. Unknown does not mean dead.

## English documentation

Generated human/model-facing documentation MUST be English subject to literal-language exceptions in `core/style-structure.md`. Code, configuration, literals, command names, API identifiers, and host-required syntax are not translated.
