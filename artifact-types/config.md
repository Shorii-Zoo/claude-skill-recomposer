# Artifact Type: Configuration / Manifest / External Integration

## Structured data rule

Treat configuration as schema-constrained data, not prose.

Capture:

- format/schema when known;
- host/runtime consumer;
- component declarations and paths;
- identifiers/namespaces;
- environment-variable placeholders;
- commands/args;
- merge/override semantics;
- discovery behavior.

## Recomposition

Merge structurally by key semantics and host rules. Preserve required unknown keys unless evidence says they are obsolete.

Update paths and identifiers atomically with the artifacts they reference.

Manifest/plugin/MCP/LSP/server configurations may define runtime-critical edges and MUST participate in runtime validation.

## Do not

- alphabetically or aesthetically rewrite config when semantics are uncertain;
- collapse two same-named keys from different scopes without understanding precedence;
- substitute secrets or environment placeholders with literal values.
