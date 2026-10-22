# Artifact Type: Agent / Subagent

## Contract

Capture:

- role and delegation trigger;
- tools and disallowed tools;
- model/effort/turn limits where relevant;
- skills/context dependencies;
- memory/background/isolation semantics;
- expected input task brief and output responsibility.

## Merge criteria

Agents MAY be consolidated only when their roles and permission/runtime contracts are compatible and callers can target the canonical role without losing useful specialization.

Prompt overlap alone is not enough.

## Recomposition

Prefer small specialist roles when separate context or restricted tool access is functionally useful. Prefer one agent with conditional behavior when separation exists only because source authors duplicated the same role.

Update all delegation edges after rename/split/merge.
