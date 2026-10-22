# Artifact Type: Command / Explicit Entrypoint

## Contract

A command is primarily an invocation interface. Capture:

- public command name;
- argument contract and placeholders;
- explicit-only activation semantics;
- orchestration target(s);
- output/interaction expectations;
- host discovery path.

## Recomposition

Prefer thin entrypoints that route to canonical underlying capabilities rather than duplicate their implementation.

Commands with overlapping behavior MAY converge on the same target while retaining separate compatibility names when useful.

If a command name changes or disappears, every known caller/documented workflow must be migrated or intentionally shimmed.

## Do not

Do not merge commands merely because their bodies are similar if their public names, arguments, user intent, or orchestration contracts differ.
