"""Deterministic long-document/RAG-style prefix generator: a second prefix
SHAPE (prose policy handbook, no tool schemas or parameters) used to check
whether the granularity/determinism findings from the tool-schema prefix
(prefix.py) generalize to prefixes in general, or are an artifact of that
one shape. Same target size (~7.7k tokens, 45 numbered sections) so
position indices are directly comparable to the tool-list sweeps.
"""

_TOPICS = [
    "Data Retention", "Access Control", "Incident Response", "Vendor Onboarding",
    "Change Management", "Password Policy", "Remote Work", "Device Encryption",
    "Backup Procedures", "Network Segmentation", "Third-Party Audits", "Code Review",
    "Release Approval", "Customer Data Handling", "Physical Security", "Travel Expenses",
    "Contractor Access", "Software Licensing", "Email Retention", "Whistleblower Protection",
    "Conflict of Interest", "Gift Acceptance", "Recruiting Standards", "Performance Review",
    "Termination Procedures", "Equipment Disposal", "Cloud Resource Tagging", "API Key Rotation",
    "Logging Standards", "Alerting Thresholds", "On-Call Rotation", "Postmortem Process",
    "Data Classification", "Encryption at Rest", "Encryption in Transit", "Multi-Factor Authentication",
    "Vulnerability Disclosure", "Patch Management", "Disaster Recovery", "Business Continuity",
    "Vendor Risk Assessment", "Export Control Compliance", "Accessibility Standards",
    "Open Source Usage", "Internal Tooling Support",
]

_SECTION_TEMPLATE = """
Section {i}: {topic}
This section establishes the requirements for {topic_lower}. All teams must
review these requirements before beginning any related work. The policy
applies uniformly across the organization regardless of team size or
project scope. Employees should consult the compliance office if any
requirement is unclear or appears to conflict with other internal
policies. Exceptions require written approval from a director-level
manager and must be documented in the internal tracking system before
implementation begins. This requirement was last revised as part of the
annual policy review cycle and supersedes any earlier guidance on the
same subject.
""".strip()


def make_prefix(n_sections: int = 45) -> str:
    header = (
        "You are a compliance assistant embedded in an internal policy "
        "portal. You have access to the sections of the employee handbook "
        "reproduced below. Always cite the specific section number when "
        "answering a policy question. Do not speculate about requirements "
        "not covered in the text below. If a question falls outside the "
        "scope of these sections, say so explicitly.\n\n"
        "Handbook sections:\n\n"
    )
    body = "\n\n".join(
        _SECTION_TEMPLATE.format(i=i, topic=_TOPICS[i - 1], topic_lower=_TOPICS[i - 1].lower())
        for i in range(1, n_sections + 1)
    )
    return header + body


def make_suffix() -> str:
    return "In one word, what office should employees consult if a requirement is unclear?"


if __name__ == "__main__":
    assert len(_TOPICS) == 45
    p = make_prefix()
    print(f"chars={len(p)} approx_tokens={len(p) // 4}")
