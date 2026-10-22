# Artifact Type: Host Adapter / Wrapper

## Role

An adapter exposes a canonical capability through a host-specific command, prompt, manifest, wrapper, or integration surface.

## Contract

Capture:

- host/runtime;
- public entrypoint;
- canonical target;
- argument/input translation;
- output translation;
- discovery/installation requirements;
- host-specific limitations.

## Recomposition

Prefer keeping shared semantic logic in one canonical capability and thin adapters per host when practical.

Do not merge adapters across hosts merely because their prose is similar. Update each adapter independently when the canonical target changes.
