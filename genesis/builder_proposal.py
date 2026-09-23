from __future__ import annotations

import re
import sys
from pathlib import Path

from genesis.builder_llm import LocalLLM
from genesis.builder_repo_reader import RepoReader


SYSTEM = """
You are the GENESIS c0ckpit engineering agent.

You are operating in PROPOSE-ONLY MODE.

HARD RULES:
- Do NOT modify files.
- Do NOT claim you modified files.
- Use only supplied repository evidence.
- Never invent files, functions, classes, or behavior.
- Distinguish confirmed facts from inference.
- Preserve existing working functionality.
- Prefer the smallest safe change.
- Identify tests that protect the proposed change.
- A possible improvement is not evidence of a defect.
- If you state that no problem is proven, PROPOSED CHANGE must be exactly None.
- If repository evidence is insufficient, request specific additional
  symbols/files instead of guessing.
"""


NO_EVIDENCE_MARKERS = (
    "no apparent problem",
    "no clear evidence",
    "not enough evidence",
    "insufficient evidence",
    "no specific proven",
)


def enforce_evidence_gate(result: str) -> str:
    """Reject a speculative change when the model admits evidence is absent."""
    lower = result.lower()
    if not any(marker in lower for marker in NO_EVIDENCE_MARKERS):
        return result

    heading = re.search(
        r"(?im)^#{0,3}\s*(?:3\.\s*)?PROPOSED CHANGE\s*$",
        result,
    )
    if not heading:
        return result

    next_heading = re.search(r"(?m)^#{0,3}\s*(?:4\.|FILES THAT WOULD CHANGE)", result[heading.end():])
    end = heading.end() + next_heading.start() if next_heading else len(result)
    proposed = result[heading.end():end].strip().lower()
    if proposed in {"none", "none."}:
        return result

    rejection = (
        "\nNone. The model stated that repository evidence did not prove a "
        "problem, so the evidence gate rejected its speculative suggestion.\n\n"
    )
    return result[:heading.end()] + rejection + result[end:]


def proposal_has_change(result: str) -> bool:
    """Return True only when the proposal section contains an evidence-backed change."""
    heading = re.search(
        r"(?im)^#{0,3}\s*(?:3\.\s*)?PROPOSED CHANGE\s*$", result
    )
    if not heading:
        return False
    next_heading = re.search(
        r"(?m)^#{0,3}\s*(?:4\.|FILES THAT WOULD CHANGE)", result[heading.end():]
    )
    end = heading.end() + next_heading.start() if next_heading else len(result)
    proposed = result[heading.end():end].strip().lower().rstrip(".")
    return bool(proposed and proposed != "none")


def build_keywords(task: str) -> list[str]:
    words = []

    for raw in task.translate(str.maketrans({"/": " ", "_": " "})).split():
        word = raw.strip(".,:;()[]{}'\"")

        if len(word) >= 4:
            words.append(word)

    # Current c0ckpit architectural anchors.
    words.extend([
        "GenerationBridge",
        "AssistantBridge",
        "MainPremiumLinux.qml",
        "FeeFeeChat.qml",
        "workflow_lab",
        "ComfyClient",
        "MediaBridge",
        "integrations",
    ])

    # Preserve order while removing duplicates.
    return list(dict.fromkeys(words))


def build_proposal(
    task: str,
    *,
    reader: RepoReader | None = None,
    llm: LocalLLM | None = None,
) -> str:
    """Return one evidence-gated proposal without modifying the repository."""
    task = task.strip()
    if not task:
        raise ValueError("Describe the GENESIS task before asking the Builder.")
    root = Path(__file__).resolve().parents[1]
    reader = reader or RepoReader(root)
    context = reader.search_context(
        build_keywords(task),
        max_chunks=12,
        max_total_chars=18000,
    )

    if not context.strip():
        raise ValueError(
            "No relevant repository context found. "
            "No proposal generated."
        )

    prompt = f"""
===== USER TASK =====

{task}

===== REPOSITORY EVIDENCE =====

{context}

===== REQUIRED RESPONSE =====

Produce a PROPOSAL ONLY.

Use these sections:

1. TASK UNDERSTANDING
2. CONFIRMED RELEVANT CODE
3. PROPOSED CHANGE
4. FILES THAT WOULD CHANGE
5. EXISTING FUNCTIONALITY THAT MUST BE PRESERVED
6. TEST PLAN
7. RISKS / UNCERTAINTIES
8. ADDITIONAL CODE NEEDED BEFORE EDITING

Do not write or modify files.
Do not output a fake claim that changes were applied.
"""

    result = (llm or LocalLLM()).chat(
        SYSTEM,
        prompt,
        max_tokens=1800,
    )
    return enforce_evidence_gate(result)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            'Usage: python -m genesis.ai_builder.propose "task description"'
        )

    task = " ".join(sys.argv[1:]).strip()

    try:
        result = build_proposal(task)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    print()
    print("========================================")
    print(" GENESIS AI BUILDER - PROPOSE ONLY")
    print("========================================")
    print()
    print(result)


if __name__ == "__main__":
    main()
