# Host & Physical Layout Policy

## Logical hierarchy is not filesystem hierarchy

Topics describe semantic containment. Host runtimes may require specific discovery paths for commands, agents, skills, hooks, configs, or executables.

Host-required placement takes precedence over visual topic nesting.

## Detect host surfaces

Infer host/discovery surfaces from explicit manifests, directory conventions, source metadata, existing managed targets, and references. Do not infer a host solely from prose when stronger structural evidence exists.

## Preserve discovery contracts

Before moving or renaming a host-discovered artifact, determine:

- how the host discovers it;
- whether its path or filename defines a public name;
- whether a manifest explicitly registers it;
- whether callers embed its path/name;
- whether path resolution uses a runtime root variable;
- whether the artifact is host-specific or portable.

Update all required declarations and consumers as one atomic change.

## Adapters

When multiple host adapters expose one canonical workflow, keep the canonical semantic core host-neutral when practical and retain separate adapters for host-specific invocation/discovery semantics.

Do not demand identical physical layouts across different hosts.

## Unsupported or unknown surfaces

If the target environment cannot represent a source runtime surface safely, preserve the artifact in managed state and report the portability limitation. Do not silently convert an active behavior into passive documentation.
