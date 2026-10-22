# Artifact Type: Skill

## Preserve

Treat skill routing metadata and invocation mode as behavior, not mere prose. Preserve or explicitly migrate:

- name/public invocation identity;
- description/trigger semantics;
- user-only vs model-invokable behavior;
- context/agent/tool restrictions where present;
- required supporting files;
- cross-skill invocation semantics.

## Recompose

Semantic content may be split or merged according to the normal focused-skill rules.

Keep the routable entrypoint compact and move detailed conditional knowledge behind direct references when useful.

When several source skills collapse into one canonical target, update all callers and retain lightweight compatibility entrypoints when removal would cause unnecessary breakage.

## Do not

- infer that two skills are equivalent solely from similar descriptions;
- convert a user-only skill into model-invokable behavior accidentally;
- hide required runtime policy only in passive references;
- break supporting-script/reference paths during re-layout.
