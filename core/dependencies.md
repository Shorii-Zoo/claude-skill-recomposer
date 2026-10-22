# Artifact & Dependency Graph

## Purpose

Topic containment is insufficient for active skill systems. Maintain an explicit graph covering semantic, invocation, runtime, data, configuration, validation, and supersession relationships.

## Edge storage

Dependencies are directed edges in the registry. Every edge MUST identify:

- stable edge id;
- `from_id`;
- `to_id`;
- relation;
- optional rationale;
- whether the edge is runtime-critical.

`from_id` and `to_id` MUST reference existing topic ids or artifact ids, including skill artifacts. Operation ids and edge ids are not valid endpoints. When a new entity type becomes a valid graph endpoint, add it explicitly to `REGISTRY.schema.json` and to this list before emitting edges against it.

## Relations

Use the narrowest useful relation. Supported relations include:

### Runtime/execution

- `invokes`
- `delegates-to`
- `executes`
- `triggered-by`
- `loads`
- `configures`
- `wraps`
- `adapts`
- `exposes`

### Data/resource

- `reads`
- `writes`
- `uses`
- `requires`

### Semantic/policy

- `complements`
- `requires-knowledge-from`
- `requires-policy-from`
- `specializes`
- `supersedes`

### Validation

- `tests`
- `validates`

Do not use graph edges to replace correct topic containment.

## Runtime-critical edges

An edge is runtime-critical when breaking it can make an entrypoint, handler, executable, delegated agent, or config stop functioning or silently change behavior.

Runtime-critical edges MUST be resolved before destructive commit.

## Supersession

When a rule, skill responsibility, entrypoint, script, reference, policy, or other artifact is superseded, preserve a traceable relation instead of erasing historical intent.

Superseded material MUST NOT remain authoritative or accidentally activatable unless it is intentionally retained as a compatibility shim.

## Maintenance

Any operation that creates, modifies, moves, splits, merges, renames, wraps, or deletes artifacts/topics MUST reevaluate affected incoming and outgoing edges.

## Validation

Detect:

- broken targets;
- dangling runtime-critical edges;
- unjustified self-dependencies;
- impossible cycles in strict `requires-*` relations;
- stale supersession edges;
- incompatible activation chains;
- executable/config path references that no longer resolve;
- adapter edges pointing to removed canonical capabilities.
