"""Controlled single-point edits to the base prefix, each at a known
character offset, for testing cache-invalidation granularity: does an edit
early in the prefix wipe out caching for everything after it (naive
whole-prefix-hash behavior), or does partial credit survive (evidence of
finer sub-block chunking)?
"""

from __future__ import annotations

from prefix import _TOOL_TEMPLATE, make_prefix


def _header() -> str:
    return make_prefix(n_tools=0)


def _blocks(n: int = 45) -> list[str]:
    return [_TOOL_TEMPLATE.format(i=i) for i in range(1, n + 1)]


def _build(header: str, blocks: list[str]) -> str:
    return header + "\n\n".join(blocks)


def _first_diff(a: str, b: str) -> int:
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    return n


def build_variants(n_tools: int = 45):
    header = _header()
    blocks = _blocks(n_tools)
    base = _build(header, blocks)

    raw = [("control", "byte-identical repeat", base)]

    mod_header = header.replace("careful, precise assistant", "meticulous, precise assistant", 1)
    raw.append(("edit_header", "single-word edit in header (position ~0%)", _build(mod_header, blocks)))

    b = list(blocks)
    b[0] = b[0].replace("Retrieves a structured record", "Fetches a structured record", 1)
    raw.append(("edit_tool1", "single-word edit in tool #1 (early)", _build(header, b)))

    mid = n_tools // 2
    b = list(blocks)
    b[mid] = b[mid].replace("Retrieves a structured record", "Fetches a structured record", 1)
    raw.append((f"edit_tool{mid+1}_mid", f"single-word edit in tool #{mid+1} (mid, ~50%)", _build(header, b)))

    b = list(blocks)
    b[-1] = b[-1].replace("Retrieves a structured record", "Fetches a structured record", 1)
    raw.append((f"edit_tool{n_tools}_late", f"single-word edit in tool #{n_tools} (last tool, ~99%)", _build(header, b)))

    raw.append(("trailing_whitespace", "single trailing space appended after full prefix (~100%)", base + " "))

    b = list(blocks)
    i, j = mid - 1, mid
    b[i], b[j] = b[j], b[i]
    raw.append((f"reorder_adjacent_{i+1}_{j+1}", f"swap adjacent tool blocks #{i+1}/#{j+1} (mid), rest byte-identical", _build(header, b)))

    out = []
    for name, desc, text in raw:
        offset = _first_diff(base, text)
        out.append(dict(name=name, desc=desc, text=text, first_diff_offset=offset,
                         frac_before_diff=(offset / len(base)) if base else 0.0))
    return base, out


if __name__ == "__main__":
    base, variants = build_variants()
    print(f"base len={len(base)}\n")
    for v in variants:
        print(f"{v['name']:28s} diff@{v['first_diff_offset']:6d} ({v['frac_before_diff']*100:5.1f}% before diff)  {v['desc']}")
