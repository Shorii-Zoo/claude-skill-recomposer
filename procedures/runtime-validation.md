# Runtime-System Validation

## Purpose

Validate active behavior in addition to semantic correctness.

## Structural validation

Where applicable verify:

- manifests/configs parse;
- declared component paths exist;
- host discovery layout is valid;
- referenced scripts exist and required executable modes are preserved;
- agent-declared skills/tools resolve;
- hook events/matchers/handlers resolve;
- command/adapter targets resolve;
- MCP/LSP/external server declarations retain required placeholders and commands;
- runtime-critical dependency edges have live targets.

## Contract validation

Compare planned target behavior against extracted source contracts. Flag unintended changes in:

- public names;
- activation mode;
- arguments/input;
- output/error semantics;
- lifecycle/order/timeout;
- permissions/tool access;
- side effects;
- environment requirements.

## Tests and evals

When owned tests/evals exist, update their targets and use them as evidence. Do not delete a failing test merely because the target architecture changed; decide whether the test encodes a preserved contract or obsolete behavior.

## Unknown active artifacts

Any unresolved unknown with potential runtime role blocks destructive deletion of its source unless explicitly preserved unchanged in the target.

## Validation output

Return pass/fail per runtime-critical artifact and a list of unverified assumptions. Semantic success does not override a runtime validation failure.
