# Artifact Type: Evaluation / Test / Fixture

## Role

Tests and evals are evidence about intended behavior, not disposable support files.

Capture:

- target artifacts/capabilities;
- setup/fixture dependencies;
- pass/fail expectations;
- host/runtime requirements;
- whether the case verifies routing, semantics, runtime contract, or integration.

## Recomposition

Update targets after rename/split/merge and preserve cases that encode retained behavior.

When conflicting tests expose genuinely changed intended behavior, resolve the policy/contract decision explicitly before rewriting expectations.

Do not delete a failing evaluation merely to make the recomposed system pass.
