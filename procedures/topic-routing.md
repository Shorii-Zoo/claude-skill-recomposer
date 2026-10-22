# Topic Routing, Creation, and Rebalancing

## Full-coverage acceptance

A topic may be selected as an integration anchor only if its semantic scope covers the entire incoming semantic material, either already or after a small coherent widening.

Do not select a topic that fits only fragments of the incoming source.

## Leaf-first search

Without explicit `--topic`, search deepest/most specialized leaf topics first, then progressively consider ancestors and more general root topics.

Choose the deepest topic that fully covers incoming semantic material without unnatural widening.

## Explicit anchor behavior

An explicitly supplied topic constrains the integration search to that topic's subtree; it MUST NOT bias placement toward the anchor itself.

After the anchor is accepted, apply normal leaf-first placement within that subtree.

For each semantic fragment, prefer the deepest/most specialized compatible descendant target, then progressively consider ancestors, using the anchor itself only when no more specialized valid target is preferable.

## Limited scope widening

A topic MAY widen slightly only when the incoming material is a natural extension of its current semantic scope and does not materially redefine descendants.

Prefer an ancestor or new topic over aggressive reinterpretation.

## No suitable topic

If no existing topic, including the most general root topic, covers all or nearly all incoming semantic material, create a new root topic.

## Distribution below anchor

Semantic units MAY be distributed into any compatible descendant topic, existing descendant skill, new skill, or new child topic. Different fragments may go to different descendants.

## Active/support artifacts

Do not apply semantic leaf-first placement mechanically to shared runtime artifacts.

An active/support artifact belongs logically at the narrowest topic scope covering its complete consumer set. Its physical path still follows host/runtime rules from `core/host-layout.md`.

## New topic rebalancing

Whenever a new topic is created, inspect every direct sibling item at that level.

Move a sibling topic only when its complete semantic scope belongs under the new topic.

Move a skill when its complete scope belongs; if only part belongs, the skill MAY be semantically split/restructured.

For shared active artifacts, reevaluate logical ownership only when the new topic contains the artifact's complete consumer set.

Apply narrowest-valid-parent recursively when obvious containment emerges. Do not restructure for visual neatness alone.
