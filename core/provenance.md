# Provenance & Managed-Output Detection

## Goal

Recomposition output must be identifiable so it cannot be fed back as ordinary source material.

## Primary provenance

The registry is authoritative for artifacts under active management and stores source lineage plus content hashes where available.

## Local markers

For generated skill directories, use `.recomposition.json` when safe.

For standalone files, a sidecar MAY be used only when the host/runtime safely ignores it. Do not introduce sidecars into discovery surfaces where extra files may alter behavior.

## Fingerprints

Store SHA-256 fingerprints for managed outputs in state. Source eligibility MUST compare explicit input paths and, when practical, exact content fingerprints against managed artifacts.

A copied exact managed output remains ineligible even when its path changed.


## External and intent source lineage

Remote GitHub source lineage MUST use canonical repository URL + exact full commit SHA + explicit subpath when present. Never persist resolver-owned temporary checkout paths as durable provenance.

Intent source lineage MUST identify the canonical intent document and its SHA-256 hash. Interactive intents use a stable intent id under `<STATE_ROOT>/intents/`; user-authored intent files use their normalized path plus content hash.

Intent documents are input evidence, not managed runtime artifacts, so the non-reentry rule for recomposition outputs does not make them ineligible for `integrate`.

## Unknown provenance

If a source appears to be managed output but local markers are absent and registry/fingerprint evidence is inconclusive, fail closed when the evidence is material rather than risking recursive recomposition.

## Provenance is not runtime policy

Do not place lineage commentary into user/model-facing skill content unless it is functionally required.
