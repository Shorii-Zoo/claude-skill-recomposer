# Topic Glossary & Terminology Governance

## Required glossary

Every topic MUST own a `GLOSSARY.md` registered by `glossary_path`.

The glossary is shared Knowledge Space, not Execution Policy.

## Recursive inheritance

Glossary visibility flows recursively:

```text
parent topic glossary
        ↓
child topic glossary
        ↓
all descendant topics and skills
```

A descendant skill may use canonical terms defined by any ancestor glossary.

## Placement rule

Place a term at the highest topic where the definition remains valid for the entire subtree.

Do not duplicate the same canonical definition in every child glossary.

## Specialization

A child MAY specialize an inherited term when its narrower scope genuinely changes the meaning. The specialization MUST explicitly reference the inherited meaning and state the narrower difference.

Silent contradictory redefinition is forbidden.

## Glossary entry shape

Prefer entries containing:

```text
Term
Definition
Optional aliases
Optional scope note
Optional parent-term relation
```

Keep glossary entries conceptual; do not hide runtime policy inside definitions.

## Maintenance

`recompose`, `integrate`, `audit --fix`, and hierarchy rebalancing MUST maintain affected glossaries.

When terms move across topic boundaries, reevaluate whether definitions should move upward, downward, remain inherited, be specialized, or be removed as dead terminology.

## Validation

Check for duplicate canonical terms, conflicting inherited definitions, unused terms where detectable, missing shared definitions, accidental policy in glossaries, and inconsistent aliases.
