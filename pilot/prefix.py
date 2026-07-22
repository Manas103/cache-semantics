"""Deterministic synthetic prefix generator: a realistic-looking system prompt +
tool-definition block, long enough to clear every provider's minimum-token
threshold for caching (OpenAI 1024, Gemini 1024-2048, Anthropic ~1024-2048).
Deterministic (no randomness) so byte-identical repeats are trivial to produce.
"""

_TOOL_TEMPLATE = """
Tool {i}: lookup_record_{i}
Description: Retrieves a structured record of type {i} from the internal knowledge
store given a primary key. Returns a JSON object with fields id, name, category,
created_at, updated_at, status, and a free-text notes field. Use this tool when the
user asks about entity type {i} specifically, not for general search queries.
Parameters:
  - record_id (string, required): the primary key of the record to fetch.
  - include_notes (boolean, optional, default false): whether to include the notes
    field in the response, which can be large.
  - fields (array of string, optional): a subset of fields to return; if omitted,
    all fields are returned.
""".strip()


def make_prefix(n_tools: int = 45) -> str:
    header = (
        "You are a careful, precise assistant embedded in an internal developer "
        "tool. You have access to a fixed set of lookup tools described below. "
        "Always confirm the record type before calling a tool. Do not guess "
        "record ids. If a user request is ambiguous, ask a clarifying question "
        "before calling any tool.\n\n"
        "Available tools:\n\n"
    )
    body = "\n\n".join(_TOOL_TEMPLATE.format(i=i) for i in range(1, n_tools + 1))
    return header + body


def make_suffix() -> str:
    return "In one word, what is the primary key field called in these tools?"


if __name__ == "__main__":
    p = make_prefix()
    print(f"chars={len(p)} approx_tokens={len(p) // 4}")
