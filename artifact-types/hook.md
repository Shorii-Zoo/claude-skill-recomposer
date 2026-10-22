# Artifact Type: Hook / Event Handler

## High-risk active surface

Hooks execute because of lifecycle events rather than semantic routing. Treat them as runtime-critical.

## Contract

Capture:

- event;
- matcher/filter;
- handler type;
- handler target;
- timeout;
- order/parallelism if relevant;
- stdin/input shape;
- stdout/response/exit semantics;
- failure behavior;
- environment/path assumptions;
- side effects.

## Recomposition

Deduplicate hooks only when event, matcher, handler semantics, and side effects are genuinely equivalent or when a safe consolidated handler preserves all behavior.

When consolidating several handlers, preserve ordering/parallel assumptions and error behavior.

## Do not

- turn a deterministic hook into model discretion without explicit intent;
- widen a matcher simply to simplify configuration;
- silently drop a handler because a similar skill exists;
- duplicate a plugin hook into another host settings surface and cause double execution.
