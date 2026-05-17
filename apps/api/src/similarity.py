"""Lightweight lexical-semantic similarity (stdlib only — no new deps).

Why not embeddings: the cheatsheet's two embedding paths are (a) VideoDB native
RTStream search — unavailable in REPLAY (no live stream) — and (b) Claude, which
has no embeddings API (architecture rule: Claude is the explanation layer only).
A vector provider would be a new dependency outside the fixed stack. For the
demo corpus (short, distinct UI scene descriptions) a normalized token-Jaccard
blended with `difflib`'s sequence ratio separates "typed correct password" from
"mistypes the password" cleanly and deterministically. Trade-off documented in
README §cost/limitations; pgvector column stays reserved for the live path.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOP = frozenset(
    "a an the is are was were be been being to of in on at by for with and or "
    "as it its this that these those user shows show showing visible appears "
    "page screen field button".split()
)


def _tokens(text: str) -> list[str]:
    return [w for w in _WORD_RE.findall(text.lower()) if w not in _STOP]


def _stem(tok: str) -> str:
    """Tiny suffix stemmer so 'mistypes'/'typed'/'typing' rhyme with 'type'."""
    for suf in ("ing", "ed", "es", "s"):
        if len(tok) > len(suf) + 2 and tok.endswith(suf):
            return tok[: -len(suf)]
    return tok


def _stems(text: str) -> list[str]:
    return [_stem(w) for w in _tokens(text)]


def score(query: str, text: str) -> float:
    """Relevance of ``text`` to ``query`` in [0, 1].

    Query-**coverage** weighted (recall of query terms in the text), not Jaccard
    — long, information-dense scene descriptions must not be penalized for
    length. Blended with a substring sequence ratio for phrase affinity, plus a
    small bonus for query terms appearing as substrings (catches stem misses).
    """
    q, t = _stems(query), _stems(text)
    if not q or not t:
        return 0.0
    qs, ts = set(q), set(t)
    coverage = len(qs & ts) / len(qs)
    raw_q, raw_t = " ".join(_tokens(query)), " ".join(_tokens(text))
    seq = SequenceMatcher(None, raw_q, raw_t).ratio()
    substr = sum(1 for w in qs if w in raw_t) / len(qs)
    return round(0.6 * coverage + 0.25 * substr + 0.15 * seq, 4)


def divergence_similarity(a: str, b: str) -> float:
    """Semantic closeness of two scene descriptions in [0, 1] (1 == same).

    Symmetric token-Jaccard blended with sequence ratio. The first aligned pair
    whose similarity drops below the divergence threshold is "where it first
    diverged".
    """
    ta, tb = _tokens(a), _tokens(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    sa, sb = set(ta), set(tb)
    jaccard = len(sa & sb) / len(sa | sb)
    seq = SequenceMatcher(None, " ".join(ta), " ".join(tb)).ratio()
    return round(0.5 * jaccard + 0.5 * seq, 4)
