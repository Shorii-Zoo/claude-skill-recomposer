# Conflict Resolution Procedure

For every conflict, identify propositions, scopes, assumptions, conditions, conflict type, surrounding rationale, and runtime consequences.

Never assume `contradiction → one source is useless`.

Never assume `both are legitimate → runtime may choose arbitrarily`.

Resolve incompatible runtime behavior in this order:

1. **Scope separation** — make different scopes explicit.
2. **General rule + exception** — encode default and exception.
3. **Conditional selection** — encode deterministic branches.
4. **Existing higher-level preference** — user/project/topic policy may decide.
5. **Default + explicit override** — preserve alternatives as knowledge but pick a runtime default.
6. **Evidence-based resolution** — only for objective contradictions; distinguish source-derived vs external evidence.
7. **Unresolved architecture decision** — do not silently ship ambiguous runtime policy.

External evidence MUST NOT turn stylistic/methodological disagreement into fake objective truth.

Track superseded rules using dependency/supersession metadata.
