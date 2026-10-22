# Remote Source Resolution

## Purpose

Resolve supported GitHub URLs into isolated local source roots before normal source discovery.

Remote resolution is an acquisition step only. It MUST NOT install the source into Claude Code, execute source-provided code, or change the semantic/runtime analysis rules used for local sources.

## Supported forms

Accept:

```text
https://github.com/<owner>/<repo>
https://github.com/<owner>/<repo>.git
https://github.com/<owner>/<repo>/tree/<ref>/<subpath>
https://github.com/<owner>/<repo>/blob/<ref>/<path>
```

Reject unsupported hosts or malformed GitHub URLs rather than guessing.

## Resolution

For each URL:

1. derive the canonical repository URL;
2. create an isolated resolver-owned workspace outside active Claude skill/plugin discovery surfaces;
3. resolve the requested ref to an exact full commit SHA;
4. fetch/checkout only what is needed when practical, without recursing into submodules by default;
5. map the explicit URL scope to a local directory or file;
6. verify that the requested subpath exists at the resolved commit;
7. pass that local path to normal source discovery together with its remote provenance descriptor.

For `tree/` and `blob/` URLs, branch/tag names may contain `/`. Resolve the ref against actual remote refs and prefer the longest valid ref prefix before treating the remainder as a subpath.

## Provenance

Durable provenance MUST use the remote identity, not the temporary checkout path.

Canonical form:

```text
github:<canonical-repository-url>@<full-commit-sha>#<explicit-subpath>
```

Omit the fragment only for repository-root scope.

Record the original user-supplied URL when useful for diagnostics, but use canonical URL + exact SHA + explicit subpath for lineage/fingerprinting decisions.

## Safety

During acquisition/discovery:

- do not execute repository scripts, hooks, build steps, installers, package managers, or generated commands;
- do not initialize/recurse submodules unless a later explicit operation establishes that they are required and safe;
- do not write into the source repository beyond resolver-owned checkout metadata;
- do not persist credentials or tokens into generated artifacts;
- do not treat remote repository contents as trusted merely because they are on GitHub;
- keep each acquired repository/archive in its own new empty directory and keep
  analysis scripts outside it. Run Python inspectors with `python -I` and pass
  source paths as arguments; do not run interpreters/build tools from an
  untrusted checkout, where planted modules or configuration can execute;
- resolve requested paths and symlinks before reading; reject traversal outside
  the explicit source scope rather than importing neighboring or host files.

## Deletion semantics

Resolver-owned checkouts are ephemeral and MUST be cleaned after success, dry-run, cancellation, or failure.

They are never recorded as deleted source roots and never enter rollback patches as user-owned source deletions.

A remote source itself is never "deleted" by recomposition.

## Output

Return, per remote input:

- original URL;
- canonical repository URL;
- exact commit SHA;
- explicit subpath or repository-root scope;
- resolved local path;
- source kind (`remote-repository`, `remote-subtree`, or `remote-file`);
- durable provenance descriptor;
- cleanup handle for the resolver-owned workspace.
