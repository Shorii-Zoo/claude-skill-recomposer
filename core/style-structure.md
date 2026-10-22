# Style & Structure Policy

## Core rule

**Preserve semantics; normalize presentation.**

Source formatting, tone, verbosity, document layout, terminology preferences, and rhetorical style are non-authoritative unless their literal form is functionally significant.

Topic-local consistency overrides source-local consistency.

## Output language

All newly generated skill instructions and documentation MUST be English regardless of source language.

Semantic normalization MUST happen before translation output so cross-language duplicates can be deduplicated.

Translation MUST preserve modality, scope, conditions, exceptions, precedence, and certainty.

Literal content MAY remain non-English only when the literal language matters, including exact strings, quotations used as data, search phrases, identifiers, code, commands, filenames, APIs, syntax, or language-specific examples.

## Canonical writing style

Default style is direct, concise, neutral, non-conversational, and operational where applicable.

Avoid rhetorical filler, motivational prose, needless introductions, and vague hedging.

Prefer `Use X when Y applies.` over prose such as `It is generally a good idea to consider...`.

## Normative vocabulary

Use consistently when behavior is normative:

- `MUST`
- `MUST NOT`
- `SHOULD`
- `SHOULD NOT`
- `MAY`
- `DEFAULT`
- `EXCEPTION`
- `OVERRIDE`

Do not mix these with vague equivalents such as `usually`, `ideally`, or `generally` when a precise normative strength is intended.

## Rule shape

Prefer explicit structures:

```text
Condition → Action
Default → Exception → Override
Constraint → Rationale
```

One rule SHOULD express one main decision.

## Layer presentation

Knowledge is descriptive and may contain alternatives.

Policy is normative, prioritized, and operationally clear.

Procedure is action-oriented and sequential where order matters.

Do not hide mandatory policy only inside reference prose.

## Canonical document structure

Use `SKILL.md`, `POLICY.md`, `PROCEDURE.md`, and `references/` according to `core/architecture.md`.

Do not create empty ceremonial sections or files.

When equivalent sections exist, keep a stable ordering. For `SKILL.md`, prefer:

```text
Purpose
Activate when
Do not activate when
Capabilities
Required policy
Procedure
References
Neighboring skills
```

## Headings and lists

- `#` for the document title.
- `##` for main sections.
- `###` for subsections.
- Avoid deeper nesting unless functionally necessary.
- Use bullets for unordered sets.
- Use numbered lists only when sequence/order matters.
- Avoid deep nested lists.

## Naming

Use `kebab-case` for skill directories and reference filenames.

Prefer capability/domain names over quality adjectives. Avoid names such as `expert-*`, `advanced-*`, `ultimate-*`, or `best-practices-*` unless the distinction is genuinely functional.

## Terminology consistency

Within a topic subtree, one concept SHOULD have one canonical term unless a distinction is semantically meaningful.

Normalize accidental synonyms. Shared terminology belongs in topic glossaries per `core/glossary.md`.

## Acronyms

Expand an acronym at first occurrence in a standalone document unless it is genuinely universal in the domain. Use the same acronym consistently throughout the topic subtree.

## Examples

Examples MUST be clearly distinguishable from normative policy and MUST NOT silently introduce rules absent from policy.

Use:

- `Invalid / Valid` for strict rule violations.
- `Bad / Better` for advisory or stylistic comparisons.

Keep examples proportional to their instructional value.

## Code, commands, paths, and literals

Use backticks for inline identifiers, paths, commands, filenames, variables, and literal values.

Use fenced blocks for code, JSON, pseudo-code, trees, and substantial structured text.

## Tone and detail-level consistency

Skills in the same topic subtree SHOULD have comparable formality and abstraction level.

Normalize depth to functional need, not source verbosity.

Do not preserve a source's extreme verbosity or terseness merely because it existed before recomposition.

## Duplication

A canonical definition or rule SHOULD live in one primary location. Duplicate only tiny critical rules that must be immediately visible.

## Topic style profiles

Every topic has an effective style profile inherited from global defaults and its parent topic.

A topic MAY refine inherited style only for a functional reason. Do not create stylistic variation for aesthetic preference alone.

Recommended profile fields include language, normative style, tone, naming, heading depth, procedure style, and example convention.

## Recompose normalization

When creating a new topic, discard presentation differences from sources, apply the global canonical style, then establish the topic profile. No source automatically becomes the style template.

## Integrate normalization

When integrating into an existing topic:

1. extract semantics without preserving source style;
2. resolve where semantic units belong;
3. inherit the effective style of each target topic;
4. rewrite incoming material into that style;
5. normalize modified existing skills when local inconsistencies become visible;
6. validate final topic consistency.

## Final style validation

Validate language, normative vocabulary, naming, terminology, section conventions, layer separation, example conventions, unjustified verbosity asymmetry, and accidental source-style remnants.

## Non-document artifact normalization

Canonical prose/style rules apply to human/model-facing documentation and comments, not blindly to executable or schema-constrained artifacts.

For scripts and code, preserve idiomatic language conventions and runtime contracts.

For structured configuration, preserve schema, key semantics, identifiers, environment placeholders, and host-required syntax.

For commands, agents, hooks, and manifests, runtime/discovery fields outrank aesthetic uniformity.

Do not rename literal public identifiers or normalize syntax merely for stylistic consistency unless every consumer is migrated safely.
