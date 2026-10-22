# Behavioral evaluations

Run these with skill-creator, using `evals.json`. This is an explicitly invoked
skill (`disable-model-invocation: true`), so automatic-trigger optimization is not
applicable.

## Protocol

1. Snapshot the implementation before editing; keep the snapshot and outputs
   outside active Claude skill/plugin discovery directories.
2. For each prompt, launch independent current-skill and original-skill runs
   together. Point each at its own entrypoint and implementation root. The
   original entrypoint before migration is commands/skill-recomposer.md.
3. Save outputs/response.md, `timing.json`, and `grading.json` per run. Grade
   actual outputs using each assertion; record evidence, not keyword matches.
4. Aggregate with skill-creator's `scripts/aggregate_benchmark.py`. That script
   currently requires `<eval>/<config>/run-1/grading.json`; the review viewer also
   accepts outputs directly under `<eval>/<config>/outputs/`.
5. Generate the viewer with `eval-viewer/generate_review.py --static`. Confirm
   the benchmark contains runs and its delta means current minus original;
   alphabetical config order can reverse the automatically computed delta.

## Initial review — 2026-11-01

Cases 1–2 were run against the original implementation and the revised entrypoint.
Independent grading: revised **5/5 assertions**, original **3/5**. Missing-state
check improved from 0/2 to 2/2; both versions passed the three untrusted-source /
shared-dependency assertions. Equal-weight per-case pass rate: 50% → 100%.

Cases 3–4 were also run in paired independent agents, covering dry-run intent
capture and transaction recovery. Both versions described safe plans on all five
assertions; these cases show no measured improvement. Their outputs and grades
remain in the external review workspace.

These are hypothetical planning evaluations, one run per version and case, not
end-to-end recomposition or rollback tests. The original sometimes resolves its
own contradictory instructions correctly; stronger wording is not evidence of
an empirical gain. Timing/token samples are diagnostic, not stable performance
estimates. Human review was deferred at the user's request for autonomous work.

## Correction coverage

Cases 5–6 cover repair of parseable invalid state versus unreadable state, and
self-exclusion/cleanup of transaction metadata for ordinary changes and rollback.
Cases 7–8 cover automatic consumption of explicit disposable local inputs for
both mutation modes. Case 9 covers managed-state restoration while preserving
and extending the operation ledger. These added scenarios are plan-level
assertions, not proof that a transaction engine ran.

Transition validation can compare a registry with a prior trusted snapshot using
`--previous-registry`; a single snapshot cannot prove append-only history.
Unit tests exercise projection digests and rejection of ledger truncation,
rewriting, and reordering.

The deterministic repository tests are separate: run
`python -m unittest discover -s tests -v` after installing
`requirements-dev.txt`. They validate structure and malformed-input handling,
not the quality or execution of a generated library.
