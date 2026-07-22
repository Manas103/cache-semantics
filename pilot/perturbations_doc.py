"""Controlled single-point edits to the doc-shape prefix (prefix_doc.py),
mirroring perturbations.py's _header/_blocks/_build helpers so the
generalization-check sweep scripts can reuse the same position-indexed
edit pattern used throughout the project for the tool-schema prefix.
"""

from __future__ import annotations

from prefix_doc import _SECTION_TEMPLATE, _TOPICS, make_prefix


def _header() -> str:
    return make_prefix(n_sections=0)


def _blocks(n: int = 45) -> list[str]:
    return [
        _SECTION_TEMPLATE.format(i=i, topic=_TOPICS[i - 1], topic_lower=_TOPICS[i - 1].lower())
        for i in range(1, n + 1)
    ]


def _build(header: str, blocks: list[str]) -> str:
    return header + "\n\n".join(blocks)


def insert_into_section(blocks: list[str], i: int, addition: str) -> list[str]:
    """Length-changing edit: append a new sentence to section i, rather than
    substituting a same-length word. Unlike every other perturbation used in
    this project, this shifts the absolute token offset of everything after
    section i -- tests whether downstream cache credit is lost entirely
    (pure prefix/LCP-continuity caching) or partially recovers (evidence of
    content-defined/rolling-hash chunking that can resync after an edit).
    """
    b = list(blocks)
    b[i] = b[i] + " " + addition
    return b
