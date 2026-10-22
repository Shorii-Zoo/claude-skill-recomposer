# Target Architecture

## Semantic layers

Every substantial target skill conceptually separates:

1. **Knowledge Space** — facts, concepts, methods, alternatives, trade-offs, examples.
2. **Execution Policy** — defaults, MUST/MUST NOT rules, precedence, exceptions, overrides.
3. **Execution Procedure** — ordered workflow that applies policy and selectively loads knowledge.

These layers govern semantic skills. They do not replace runtime artifact types such as hooks, scripts, commands, or agents.

## Default semantic skill layout

```text
skill-name/
├── SKILL.md
├── POLICY.md
├── PROCEDURE.md
├── references/
│   └── ...
└── .recomposition.json
```

Small skills MAY colocate layers when physical separation would add indirection, but the conceptual boundaries MUST remain explicit.

`.recomposition.json` is optional: use it only when the host safely ignores the sidecar; otherwise keep provenance and fingerprints in state per `core/provenance.md`.

## SKILL.md

Routing/orchestration entrypoint. Keep compact. It SHOULD contain purpose, activation conditions, non-activation boundaries when useful, required policy/procedure loading, conditional references, and neighboring-skill distinctions.

## POLICY.md

Authoritative runtime behavior. It SHOULD encode mandatory behavior, defaults, prohibitions, precedence, exceptions, overrides, failure behavior, and decision criteria.

## PROCEDURE.md

Execution sequence. It SHOULD contain ordered steps, branches, checks, selective resource loading, validation, and completion criteria. It MUST reference policy rather than silently redefine it.

## references/

Primary per-skill Knowledge Space. It MAY contain multiple legitimate approaches, theory, standards, examples, edge cases, templates, and detailed guidance.

## Runtime/support artifacts

Commands, agents, hooks, scripts, configs, rules, adapters, and evaluations remain first-class artifacts. They MAY belong to or support one or more semantic skills but MUST retain their own runtime contracts and host-required layouts.

Do not force all runtime material into `SKILL.md`, `POLICY.md`, `PROCEDURE.md`, or `references/`.

## Logical vs physical architecture

The topic tree is a logical semantic hierarchy. Physical paths MUST also satisfy host discovery and runtime requirements.

A topic relationship MUST NOT cause a command, agent, hook, manifest, executable, or other host-discovered artifact to be moved into an invalid physical location.

Use registry membership and dependency edges to express logical ownership when physical nesting would break discovery.

## Topic-level shared knowledge

Each topic owns a `GLOSSARY.md` and MAY own other shared knowledge when several descendants need it. Do not create an artificial skill merely to host shared knowledge.

## Topic-level active support

A topic MAY own shared active support artifacts when their full consumer set lies inside that subtree. Place them according to host/runtime layout, not merely inside the topic's filesystem folder.
