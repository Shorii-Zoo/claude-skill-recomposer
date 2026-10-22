# Artifact Type: Script / Executable Helper

## Contract

Capture:

- runtime/interpreter;
- invocation path;
- arguments and stdin;
- stdout/stderr format;
- exit codes;
- environment variables;
- files/network/process side effects;
- executable mode;
- callers;
- platform assumptions.

## Recomposition

Prefer scripts for deterministic/repetitive mechanics when that avoids large inline instruction blocks.

Scripts MAY be shared when their complete consumer set can use one contract. Otherwise keep specialized variants.

Renames/moves require caller rewrites and executable-mode preservation.

## Do not

Do not rewrite a working script into prose, or merge scripts solely from textual similarity. Behavioral compatibility and caller migration are mandatory.
