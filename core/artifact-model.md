# Managed Artifact Model

## Why artifacts exist

A recomposed capability can span several files with different runtime roles. Model those roles explicitly instead of treating every file as a knowledge document.

## Canonical artifact kinds

Use the narrowest applicable kind:

- `skill` — routable workflow/instruction bundle;
- `command` — explicit user-facing entrypoint or compatibility shim;
- `agent` — delegated execution context/persona with its own tool or runtime contract;
- `hook` — lifecycle/event-triggered handler configuration;
- `script` — executable helper or runtime program;
- `rule` — persistent or broadly scoped instruction/policy surface;
- `config` — structured manifest, MCP/LSP/server, plugin, host, or runtime configuration;
- `reference` — knowledge, template, example, asset, or supporting material loaded/consumed on demand;
- `evaluation` — test, eval, fixture, or validation artifact used to prove behavior;
- `adapter` — host-specific wrapper exposing a canonical capability through another harness/surface;
- `unknown` — material whose role is not yet safely classified.

A physical file may contribute to more than one conceptual role. Split the model logically without corrupting the physical format.

## Artifact scope

Classify each discovered artifact as one of:

- `runtime` — participates in end-user/agent behavior;
- `distribution` — installation, manifest, packaging, or discovery metadata;
- `validation` — tests/evals/fixtures/checkers;
- `development` — config/docs used to maintain the source repository itself;
- `documentation` — human documentation not required at runtime;
- `unknown`.

Repository-development files MUST NOT automatically become recomposed runtime assets.

## Activation modes

Record the effective activation mode when relevant:

- `model` — selected automatically from semantic routing;
- `user` — explicit invocation;
- `event` — hook/lifecycle driven;
- `delegated` — invoked by another agent/workflow;
- `external` — called by an external system/process;
- `none` — passive resource;
- `unknown`.

Activation mode is part of behavior. Do not change it accidentally during semantic consolidation.

## Runtime contract

For active artifacts, capture the contract dimensions that matter for compatibility:

- public name or invocation identifier;
- trigger/event/matcher;
- caller and consumers;
- accepted arguments/input shape;
- output shape and communication channel;
- exit/error semantics;
- environment variables and secrets references;
- tools/permissions/model/isolation when applicable;
- filesystem/network/process side effects;
- path-resolution assumptions;
- ordering, timeout, concurrency, and lifecycle semantics;
- host/discovery surface.

Not every kind uses every dimension.

## Canonical capability vs adapters

When several host-specific wrappers expose the same underlying workflow, represent one canonical semantic capability plus separate adapters/entrypoints when that reduces duplication without breaking host behavior.

Do not merge host-specific wrapper files merely because their prose is similar. Preserve the adapter boundary and update each adapter to the canonical target where safe.

## Shared active artifacts

Scripts, references, configs, and other support artifacts used by multiple skills SHOULD live at the narrowest ownership scope that covers their complete consumer set.

Do not duplicate shared executables solely to fit the topic tree.
