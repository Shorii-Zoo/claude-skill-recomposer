#!/usr/bin/env python3
"""Deterministic sparse thematic clustering for plugin and topic records.

The public API is :func:`cluster_items`.  It builds TF-IDF vectors from names,
descriptions, and optional text, then joins items whose similarity meets a
threshold.  Clusters are cohesive and agglomerate strongest edges first: two
clusters merge only when every cross-pair is similar, so one broad mixed bundle
cannot chain unrelated focused domains together.  Components are returned as
``{"label": str, "items": [...]}``;
singletons are included and empty input returns ``[]``.  Groups are sorted by
label and members by ``id``; the original dictionaries are never mutated.

Performance policy:
* For sets of at least 64 items, posting lists longer than
  ``max(16, min(256, n // 10))`` are treated as common and are excluded from
  both the sparse vectors and candidate expansion.  Smaller sets are not
  capped because a token shared by every item can still be their theme.  The
  cap is deliberate: harness boilerplate and generic words must not create
  giant components.  Items whose only tokens are common are still returned as
  singletons; no item is ever dropped.
* At most ``MAX_CANDIDATES_PER_ITEM`` neighbours are examined per item,
  preferring tokens with the smallest posting lists.  This bounds work on
  dense or adversarial inputs at the cost of possibly missing an edge through
  a very common token, which is already outside the conservative policy.
* Text fields use a deterministic, evenly spread sample of source words to
  bound memory without favoring only the beginning of a concatenated bundle.
* Optional ``segments`` are sampled deterministically to at most
  ``MAX_SEGMENTS_PER_ITEM`` and compared through the same bounded candidate
  index.  An item pair links if its aggregate vectors are similar or any
  sampled segment pair is similar.

Limitations:
* This is lexical, not semantic.  Synonyms with unrelated spellings do not
  match, and no language model or embeddings are used.
* English-oriented suffix folding is intentionally small.  It handles common
  plural, ``-ing``, ``-ed``, ``-ization`` and ``-ation`` forms without product
  name exceptions.  Domain-agnostic operations such as audit, review, check,
  validate and inspect are ignored.
* ``text`` keeps an evenly spread sample of up to 1024 words, so late metadata
  is not discarded merely because sources were concatenated in alphabetical
  order.  With ``segments``, the local subtheme comparison is direct; without
  them, aggregate text still dilutes a small shared subtheme.
* At most 32 segments per item are compared.  Larger segment lists are sampled
  evenly across their original order, so an unexamined segment cannot link.
* Cohesion is enforced greedily with complete-link merges ordered by descending
  edge strength (cosine, then overlap, then sorted id).  This prevents
  transitive bridges and weak early edges from stealing a stronger pair, but an
  item that genuinely belongs to two domains is assigned to only one cluster.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import math
import re
from typing import Any, Iterable

DEFAULT_THRESHOLD = 0.34
MAX_CANDIDATES_PER_ITEM = 512
_MIN_COMMON_POSTINGS = 16
_MAX_COMMON_POSTINGS = 256
_COMMON_DIVISOR = 10
_MIN_SET_FOR_COMMON_CAP = 64
_ITEM_FIELD_SPECS = (("name", 3, 64), ("description", 1, 512))
_TEXT_WORD_LIMIT = 1024
_SEGMENT_WORD_LIMIT = 512
MAX_SEGMENTS_PER_ITEM = 32
_VALID_KINDS = frozenset({"plugin", "topic"})

_WORD_RE = re.compile(r"[A-Za-z0-9]+")
_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")

# Domain-agnostic operation words do not describe a shared subject.  Excluding
# them prevents segments from bridging solely on "audit", "review", and similar
# verbs, while domain nouns such as security, code, document and test remain.
_GENERIC_OPERATIONS = frozenset({
    "analyze", "analyzes", "analyzing", "analysis", "assess", "assesses",
    "assessing", "assessment", "audit", "audits", "auditing", "check",
    "checks", "checking", "evaluate", "evaluates", "evaluating", "evaluation",
    "examine", "examines", "examining", "execute", "executes", "executing",
    "handle", "handles", "handling", "inspect", "inspects", "inspecting",
    "inspection", "manage", "managed", "manages", "managing", "management",
    "operation", "operations", "perform", "performs", "performing", "review",
    "reviews", "reviewing", "validate", "validates", "validating",
    "validation", "verify", "verifies", "verifying", "verification",
})

# Generic English and agent-harness vocabulary.  Topical words such as data,
# image, document, api, security, browser, test and knowledge are intentionally
# left out.
_STOPWORDS = frozenset({
    "a", "about", "above", "after", "again", "against", "all", "also", "am",
    "an", "and", "any", "are", "as", "at", "be", "because", "been", "before",
    "being", "below", "between", "both", "but", "by", "can", "could", "did",
    "do", "does", "doing", "down", "during", "each", "few", "for", "from",
    "further", "had", "has", "have", "having", "he", "her", "here", "hers",
    "herself", "him", "himself", "his", "how", "i", "if", "in", "into", "is",
    "it", "its", "itself", "just", "me", "more", "most", "my", "myself", "no",
    "nor", "not", "now", "of", "off", "on", "once", "only", "or", "other",
    "our", "ours", "ourselves", "out", "over", "own", "same", "she", "should",
    "so", "some", "such", "than", "that", "the", "their", "theirs", "them",
    "themselves", "then", "there", "these", "they", "this", "those", "through",
    "to", "too", "under", "until", "up", "very", "was", "we", "were", "what",
    "when", "where", "which", "while", "who", "whom", "why", "will", "with",
    "would", "you", "your", "yours", "yourself", "yourselves",
    "across", "around", "based", "boilerplate", "common", "component",
    "components", "example", "examples", "extension", "extensions", "fixture",
    "frameworks", "generic", "helper", "item", "items", "library", "libraries",
    "module", "modules", "package", "packages", "per", "sample", "samples",
    "shared", "topic", "topics", "utility", "utilities", "widget", "within",
    "without",
    "agent", "agents", "anthropic", "assistant", "claude", "codex", "command",
    "commands", "create", "creates", "creating", "description", "descriptions",
    "enable", "enabled", "enables", "enabling", "expert", "file", "files",
    "help", "helps", "helping", "include", "includes", "including", "make",
    "makes", "making", "manage", "manages", "managing", "name", "names",
    "optional", "plugin", "plugins", "project", "projects", "provide",
    "provided", "provides", "providing", "run", "runs", "running", "skill",
    "skills", "support", "supported", "supports", "task", "tasks", "text",
    "tool", "tools", "use", "used", "user", "users", "uses", "using", "via",
    "workflow", "workflows",
}) | _GENERIC_OPERATIONS


class _UnionFind:
    __slots__ = ("parent", "rank")

    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, item: int) -> int:
        parent = self.parent
        root = item
        while parent[root] != root:
            root = parent[root]
        while parent[item] != item:
            parent[item], item = root, parent[item]
        return root

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        if self.rank[left_root] < self.rank[right_root]:
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        if self.rank[left_root] == self.rank[right_root]:
            self.rank[left_root] += 1


def _undouble(word: str) -> str:
    if len(word) > 2 and word[-1] == word[-2] and word[-1] not in "lsz":
        return word[:-1]
    return word


def _stem(word: str) -> str:
    """Fold simple English suffixes; no dictionary or product exceptions."""
    if len(word) <= 3:
        return word
    if word.endswith("ies") and len(word) > 4:
        word = word[:-3] + "y"
    elif word.endswith(("sses", "shes", "ches", "xes", "zes")):
        word = word[:-2]
    elif word.endswith("s") and not word.endswith(("ss", "us", "is")):
        word = word[:-1]

    if word.endswith("ization") and len(word) > 7:
        word = word[:-7] + "ize"
    elif word.endswith("isation") and len(word) > 7:
        word = word[:-7] + "ise"
    elif word.endswith("ation") and len(word) > 6:
        word = word[:-5] + "ate"

    if word.endswith("ing") and len(word) > 5:
        word = _undouble(word[:-3])
        if word.endswith(("at", "iz", "iv", "ur")):
            word += "e"
    elif word.endswith("ed") and len(word) > 4:
        word = _undouble(word[:-2])
        if word.endswith("i"):
            word = word[:-1] + "y"
        elif word.endswith(("at", "iz", "iv", "ur")):
            word += "e"
    elif word.endswith("ly") and len(word) > 5:
        word = word[:-2]
    return word


_STOPWORD_STEMS = frozenset(_stem(word) for word in _STOPWORDS) | _STOPWORDS


def _sampled_words(value: str, limit: int) -> list[str]:
    if limit <= 0:
        return []
    words = _WORD_RE.findall(value)
    if len(words) <= limit:
        return words
    if limit == 1:
        return words[-1:]
    return [
        words[(index * (len(words) - 1)) // (limit - 1)]
        for index in range(limit)
    ]


def _normalized_tokens(value: str, limit: int, counts: Counter[str], weight: int) -> None:
    for raw_word in _sampled_words(value, limit):
        for piece in _CAMEL_BOUNDARY_RE.split(raw_word):
            token = _stem(piece.lower())
            if len(token) >= 2 and token not in _STOPWORD_STEMS and any(ch.isalpha() for ch in token):
                counts[token] += weight


def _selected_segments(item: dict[str, Any]) -> list[str]:
    segments = item.get("segments")
    if not segments:
        return []
    if len(segments) <= MAX_SEGMENTS_PER_ITEM:
        return list(segments)
    return [
        segments[(index * (len(segments) - 1)) // (MAX_SEGMENTS_PER_ITEM - 1)]
        for index in range(MAX_SEGMENTS_PER_ITEM)
    ]


def _tokenize_item(item: dict[str, Any]) -> tuple[Counter[str], list[Counter[str]]]:
    counts: Counter[str] = Counter()
    for field, weight, limit in _ITEM_FIELD_SPECS:
        value = item.get(field, "")
        if value:
            _normalized_tokens(value, limit, counts, weight)

    segments = _selected_segments(item)
    segment_counts = []
    if segments:
        for segment in segments:
            segment_count: Counter[str] = Counter()
            _normalized_tokens(segment, _SEGMENT_WORD_LIMIT, segment_count, 1)
            segment_counts.append(segment_count)
            counts.update(segment_count)
    else:
        text = item.get("text", "")
        if text:
            _normalized_tokens(text, _TEXT_WORD_LIMIT, counts, 1)
    return counts, segment_counts


def _id_key(value: Any) -> tuple[str, str]:
    return type(value).__name__, str(value)


def _validate_and_prepare(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    if items is None:
        raise ValueError("items must be an iterable of item dictionaries")
    try:
        prepared = list(items)
    except TypeError as exc:
        raise ValueError("items must be an iterable of item dictionaries") from exc

    seen_ids: set[Any] = set()
    for item in prepared:
        if not isinstance(item, dict):
            raise ValueError("each item must be a dictionary")
        missing = [field for field in ("id", "kind", "name", "description") if field not in item]
        if missing:
            raise ValueError(f"item is missing required fields: {', '.join(missing)}")
        identifier = item["id"]
        try:
            if identifier in seen_ids:
                raise ValueError(f"duplicate item id: {identifier!r}")
            seen_ids.add(identifier)
        except TypeError as exc:
            raise ValueError("item ids must be hashable") from exc
        if item["kind"] not in _VALID_KINDS:
            raise ValueError(f"invalid kind for item {identifier!r}: {item['kind']!r}")
        for field in ("name", "description"):
            if not isinstance(item[field], str):
                raise ValueError(f"{field} for item {identifier!r} must be a string")
        if "text" in item and item["text"] is not None and not isinstance(item["text"], str):
            raise ValueError(f"text for item {identifier!r} must be a string or None")
        segments = item.get("segments")
        if segments is not None and (
            not isinstance(segments, (list, tuple))
            or not all(isinstance(segment, str) for segment in segments)
        ):
            raise ValueError(f"segments for item {identifier!r} must be a list of strings")
    prepared.sort(key=lambda item: _id_key(item["id"]))
    return prepared


def _common_posting_limit(size: int) -> int:
    if size < _MIN_SET_FOR_COMMON_CAP:
        return size
    return max(_MIN_COMMON_POSTINGS, min(_MAX_COMMON_POSTINGS, size // _COMMON_DIVISOR))


def _vectorize(
    counts: Counter[str],
    document_frequency: dict[str, int],
    size: int,
    posting_limit: int,
) -> dict[str, float]:
    weighted: dict[str, float] = {}
    for token, count in counts.items():
        frequency = document_frequency.get(token, 0)
        if not frequency or frequency > posting_limit:
            continue
        tf = 1.0 + math.log(count)
        idf = math.log((size + 1.0) / (frequency + 1.0)) + 1.0
        weighted[token] = tf * idf
    norm = math.sqrt(sum(value * value for value in weighted.values()))
    return {token: value / norm for token, value in weighted.items()} if norm else {}


def _build_vectors(
    token_counts: list[Counter[str]],
) -> tuple[list[dict[str, float]], dict[str, int], int]:
    size = len(token_counts)
    document_frequency: Counter[str] = Counter()
    for counts in token_counts:
        document_frequency.update(counts.keys())

    posting_limit = _common_posting_limit(size)
    vectors = [
        _vectorize(counts, document_frequency, size, posting_limit)
        for counts in token_counts
    ]
    return vectors, dict(document_frequency), posting_limit


def _candidate_neighbours(
    vectors: list[dict[str, float]], document_frequency: dict[str, int]
) -> list[set[int]]:
    postings: dict[str, list[int]] = defaultdict(list)
    for index, vector in enumerate(vectors):
        for token in sorted(vector):
            postings[token].append(index)

    posting_limit = _common_posting_limit(len(vectors))
    candidates: list[set[int]] = [set() for _ in vectors]
    for index, vector in enumerate(vectors):
        if not vector:
            continue
        for token in sorted(vector, key=lambda value: (len(postings[value]), value)):
            if document_frequency[token] > posting_limit:
                continue
            neighbours = postings[token]
            if len(neighbours) <= 1:
                continue
            candidates[index].update(neighbour for neighbour in neighbours if neighbour != index)
            if len(candidates[index]) >= MAX_CANDIDATES_PER_ITEM:
                break
    return candidates


def _add_segment_candidates(
    candidates: list[set[int]], segment_vectors: list[list[dict[str, float]]]
) -> None:
    total_segments = sum(len(segments) for segments in segment_vectors)
    if not total_segments:
        return

    postings: dict[str, list[int]] = defaultdict(list)
    for item_index, segments in enumerate(segment_vectors):
        for vector in segments:
            for token in sorted(vector):
                postings[token].append(item_index)

    posting_limit = _common_posting_limit(total_segments)
    for item_index, segments in enumerate(segment_vectors):
        if not segments or len(candidates[item_index]) >= MAX_CANDIDATES_PER_ITEM:
            continue
        tokens = {token for vector in segments for token in vector}
        for token in sorted(tokens, key=lambda value: (len(postings[value]), value)):
            if len(postings[token]) > posting_limit:
                continue
            candidates[item_index].update(
                other for other in postings[token] if other != item_index
            )
            if len(candidates[item_index]) >= MAX_CANDIDATES_PER_ITEM:
                break


def _segment_token_index(
    segment_vectors: list[list[dict[str, float]]],
) -> list[dict[str, list[int]]]:
    result = []
    for segments in segment_vectors:
        index: dict[str, list[int]] = defaultdict(list)
        for segment_index, vector in enumerate(segments):
            for token in vector:
                index[token].append(segment_index)
        result.append(dict(index))
    return result


def _segment_edge_evidence(
    left_index: int,
    right_index: int,
    segment_vectors: list[list[dict[str, float]]],
    segment_index: list[dict[str, list[int]]],
    threshold: float,
) -> tuple[float, float] | None:
    left_segments = segment_vectors[left_index]
    right_segments = segment_vectors[right_index]
    if not left_segments or not right_segments:
        return None
    if len(left_segments) > len(right_segments):
        left_index, right_index = right_index, left_index
        left_segments, right_segments = right_segments, left_segments
    other_index = segment_index[right_index]
    best = None
    for left_vector in left_segments:
        seen = set()
        for token in left_vector:
            for right_segment_index in other_index.get(token, ()):
                if right_segment_index in seen:
                    continue
                seen.add(right_segment_index)
                evidence = _edge_evidence(
                    left_vector, right_segments[right_segment_index], threshold
                )
                if evidence is not None and (best is None or evidence > best):
                    best = evidence
    return best


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(token, 0.0) for token, value in left.items())


def _edge_evidence(
    left: dict[str, float], right: dict[str, float], threshold: float
) -> tuple[float, float] | None:
    if not left or not right:
        return None
    cosine = _cosine(left, right)
    if len(left) > len(right):
        left, right = right, left
    shared = sum(1 for token in left if token in right)
    overlap = shared / len(left)
    if cosine >= threshold or (shared >= 2 and overlap >= max(0.5, threshold)):
        return cosine, overlap
    return None


def _similar(
    left: dict[str, float], right: dict[str, float], threshold: float
) -> bool:
    return _edge_evidence(left, right, threshold) is not None


def _cohesive_components(
    vectors: list[dict[str, float]],
    candidates: list[set[int]],
    segment_vectors: list[list[dict[str, float]]],
    segment_index: list[dict[str, list[int]]],
    threshold: float,
) -> list[list[int]]:
    """Greedy complete-link components from the bounded candidate graph."""
    size = len(vectors)
    adjacency: list[set[int]] = [set() for _ in range(size)]
    edges: list[tuple[float, float, int, int]] = []
    for left_index, neighbours in enumerate(candidates):
        for right_index in sorted(neighbours):
            if right_index == left_index:
                continue
            if right_index < left_index and left_index in candidates[right_index]:
                continue
            evidence = _edge_evidence(
                vectors[left_index], vectors[right_index], threshold
            )
            segment_evidence = _segment_edge_evidence(
                left_index, right_index, segment_vectors, segment_index, threshold
            )
            if segment_evidence is not None and (
                evidence is None or segment_evidence > evidence
            ):
                evidence = segment_evidence
            if evidence is None:
                continue
            adjacency[left_index].add(right_index)
            adjacency[right_index].add(left_index)
            edges.append((evidence[0], evidence[1], left_index, right_index))

    edges.sort(key=lambda edge: (-edge[0], -edge[1], edge[2], edge[3]))
    union_find = _UnionFind(size)
    members: dict[int, list[int]] = {index: [index] for index in range(size)}
    for _, _, left_index, right_index in edges:
        left_root = union_find.find(left_index)
        right_root = union_find.find(right_index)
        if left_root == right_root:
            continue
        left_members = members[left_root]
        right_members = members[right_root]
        if not all(
            other in adjacency[member]
            for member in left_members
            for other in right_members
        ):
            continue
        union_find.union(left_root, right_root)
        new_root = union_find.find(left_root)
        members[new_root] = left_members + right_members
        members.pop(right_root if new_root == left_root else left_root, None)

    grouped: dict[int, list[int]] = defaultdict(list)
    for index in range(size):
        grouped[union_find.find(index)].append(index)
    return list(grouped.values())


def _component_label(
    member_indices: list[int], items: list[dict[str, Any]], vectors: list[dict[str, float]]
) -> str:
    if len(member_indices) == 1:
        name = items[member_indices[0]]["name"].strip()
        if name:
            return name

    document_frequency: Counter[str] = Counter()
    weight: Counter[str] = Counter()
    for index in member_indices:
        for token, value in vectors[index].items():
            document_frequency[token] += 1
            weight[token] += value

    shared = [token for token in document_frequency if document_frequency[token] > 1]
    ranked = sorted(
        shared,
        key=lambda token: (-document_frequency[token], -weight[token], token),
    )[:2]
    if not ranked:
        ranked = sorted(weight, key=lambda token: (-weight[token], token))[:2]
    if ranked:
        return "-".join(ranked)

    for index in member_indices:
        name = items[index]["name"].strip()
        if name:
            return name
    return "unlabeled"


def cluster_items(
    items: Iterable[dict[str, Any]], threshold: float = DEFAULT_THRESHOLD
) -> list[dict[str, Any]]:
    """Cluster plugin/topic dictionaries by sparse thematic similarity.

    ``items`` holds dictionaries with ``id``, ``kind`` (``plugin`` or
    ``topic``), ``name``, ``description``, optional ``text``, and optional
    ``segments`` (a list of per-source description strings).  Inputs are not
    modified.  The result is a deterministically ordered list of
    ``{"label": str, "items": [original dictionaries]}`` components.  Every
    input appears exactly once, and singleton components are retained.

    Similarity is cosine over TF-IDF vectors built from names, descriptions
    and either segments or text (non-empty segments replace text for that
    item).  A pair also links when it shares at least two
    content tokens and those tokens cover half of the smaller item's
    vocabulary (or ``threshold`` when that is stricter), or when one pair of
    their segments is similar by the same rule.  The overlap and segment rules
    keep short or broad records useful without letting a single generic token
    connect unrelated items.  Pass a lower threshold for broader recall or a
    higher value for tighter themes.  Common tokens whose posting list exceeds
    the documented limit are excluded to prevent generic boilerplate from
    producing giant components.
    """
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not math.isfinite(threshold)
        or threshold < 0.0
        or threshold > 1.0
    ):
        raise ValueError("threshold must be a finite number between 0 and 1")

    prepared = _validate_and_prepare(items)
    if not prepared:
        return []

    tokenized = [_tokenize_item(item) for item in prepared]
    token_counts = [counts for counts, _ in tokenized]
    vectors, document_frequency, posting_limit = _build_vectors(token_counts)
    segment_vectors = [
        [
            _vectorize(segment, document_frequency, len(prepared), posting_limit)
            for segment in segments
        ]
        for _, segments in tokenized
    ]
    candidates = _candidate_neighbours(vectors, document_frequency)
    _add_segment_candidates(candidates, segment_vectors)
    segment_index = _segment_token_index(segment_vectors)

    components = _cohesive_components(
        vectors, candidates, segment_vectors, segment_index, threshold
    )

    groups = []
    for member_indices in components:
        member_indices.sort(key=lambda index: _id_key(prepared[index]["id"]))
        groups.append(
            {
                "label": _component_label(member_indices, prepared, vectors),
                "items": [prepared[index] for index in member_indices],
            }
        )
    groups.sort(key=lambda group: (group["label"], [_id_key(item["id"]) for item in group["items"]]))
    return groups
