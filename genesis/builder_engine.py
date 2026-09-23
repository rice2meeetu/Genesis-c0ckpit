"""Reviewed, repository-bounded code changes for the local Builder."""

from __future__ import annotations

import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from genesis.builder_llm import LocalLLM
from genesis.builder_repo_reader import RepoReader


ALLOWED_SUFFIXES = {".py", ".qml", ".json", ".md", ".txt", ".toml", ".yaml", ".yml"}
MAX_PATCH_BYTES = 120_000
PROTECTED_NAMES = {"main.py.COCKPIT_GOOD_20260903-025426"}


SYSTEM = """You are the local GENESIS engineering agent. Produce one minimal unified
git diff for the requested change, using only the supplied repository evidence.
Return the diff only, beginning with 'diff --git'. Do not use Markdown fences.
Do not add dependencies, shell commands, binary files, secrets, network calls,
systemd changes, GitHub workflow changes, or edits outside the repository. Preserve
existing behavior and add focused tests when appropriate.
If evidence is insufficient, return exactly: NO_SAFE_PATCH
"""


@dataclass(frozen=True)
class ApplyResult:
    applied: bool
    tests_passed: bool
    output: str
    original_branch: str = ""
    builder_branch: str = ""


def _extract_patch(text: str) -> str:
    text = text.strip()
    if text == "NO_SAFE_PATCH":
        raise ValueError("Builder did not have enough evidence for a safe patch")
    start = text.find("diff --git ")
    if start < 0:
        raise ValueError("Builder response did not contain a unified git diff")
    patch = text[start:].replace("```diff", "").replace("```", "").strip() + "\n"
    validate_patch(patch)
    return patch


def patch_paths(patch: str) -> tuple[str, ...]:
    paths = []
    for old, new in re.findall(r"^diff --git a/(.+) b/(.+)$", patch, re.MULTILINE):
        if old != new:
            raise ValueError("renames are not supported by the reviewed Builder")
        paths.append(new)
    return tuple(dict.fromkeys(paths))


def validate_patch(patch: str) -> tuple[str, ...]:
    if len(patch.encode("utf-8")) > MAX_PATCH_BYTES:
        raise ValueError("patch exceeds the 120 KB review limit")
    if "GIT binary patch" in patch or "Binary files " in patch:
        raise ValueError("binary patches are not supported")
    if "deleted file mode" in patch:
        raise ValueError("file deletion is not supported by Build Mode")
    paths = patch_paths(patch)
    if not paths:
        raise ValueError("patch contains no file changes")
    for raw in paths:
        path = Path(raw)
        if path.is_absolute() or ".." in path.parts or path.name in PROTECTED_NAMES:
            raise ValueError(f"protected or external path: {raw}")
        if path.suffix.lower() not in ALLOWED_SUFFIXES:
            raise ValueError(f"unsupported file type: {raw}")
        if any(part in {".git", ".github", "systemd"} for part in path.parts):
            raise ValueError(f"protected infrastructure path: {raw}")
    return paths


def draft_change(
    task: str,
    root: str | Path,
    proposal: str = "",
    llm: LocalLLM | None = None,
) -> str:
    task = task.strip()
    if not task:
        raise ValueError("describe the code change first")
    root = Path(root).resolve()
    context = RepoReader(root).search_context(
        [word for word in re.findall(r"[A-Za-z_]{4,}", task)][:24]
        + [
            "GenerationBridge", "AssistantBridge", "MainPremiumLinux.qml",
            "FeeFeeChat.qml", "workflow_lab", "ComfyClient", "MediaBridge",
        ],
        max_chunks=18,
        max_total_chars=28_000,
    )
    if not context:
        raise ValueError("no relevant repository evidence found")
    accepted = proposal.strip()
    prompt = f"USER REQUEST:\n{task}\n\nREPOSITORY EVIDENCE:\n{context}"
    if accepted:
        prompt += f"\n\nACCEPTED EVIDENCE-GATED PROPOSAL:\n{accepted}"
    answer = (llm or LocalLLM()).chat(
        SYSTEM,
        prompt,
        max_tokens=5000,
    )
    return _extract_patch(answer)


def _run(root: Path, args: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=root, input=input_text, text=True, capture_output=True, timeout=600)


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return _run(root, ["git", *args])


def _clean_status(root: Path) -> bool:
    status = _git(root, "status", "--porcelain")
    return status.returncode == 0 and not status.stdout.strip()


def apply_and_test(root: str | Path, patch: str) -> ApplyResult:
    root = Path(root).resolve()
    validate_patch(patch)
    if not _clean_status(root):
        raise RuntimeError("GENESIS repository must be clean before Build Mode applies a patch")

    original_branch = _git(root, "branch", "--show-current").stdout.strip() or "main"
    builder_branch = "builder/" + time.strftime("%Y%m%d-%H%M%S")
    branch = _git(root, "switch", "-c", builder_branch)
    if branch.returncode:
        raise RuntimeError(branch.stderr.strip() or "Could not create Builder branch")

    check = _run(root, ["git", "apply", "--check", "-"], input_text=patch)
    if check.returncode:
        _git(root, "switch", original_branch)
        _git(root, "branch", "-D", builder_branch)
        return ApplyResult(
            False, False, "Patch check failed:\n" + check.stderr.strip(),
            original_branch, builder_branch,
        )

    applied = _run(root, ["git", "apply", "-"], input_text=patch)
    if applied.returncode:
        _git(root, "switch", original_branch)
        _git(root, "branch", "-D", builder_branch)
        return ApplyResult(
            False, False, "Patch apply failed:\n" + applied.stderr.strip(),
            original_branch, builder_branch,
        )

    tests = _run(root, [sys.executable, "-m", "pytest", "-q"])
    output = (tests.stdout + "\n" + tests.stderr).strip()
    if tests.returncode:
        rollback = _run(root, ["git", "apply", "-R", "-"], input_text=patch)
        if rollback.returncode == 0 and _clean_status(root):
            _git(root, "switch", original_branch)
            _git(root, "branch", "-D", builder_branch)
            output += "\nPatch rolled back after test failure."
        else:
            output += "\nAutomatic rollback needs inspection; Builder branch retained."
        return ApplyResult(False, False, output, original_branch, builder_branch)

    return ApplyResult(True, True, output, original_branch, builder_branch)


def commit_applied(
    root: str | Path,
    patch: str,
    task: str,
    original_branch: str = "main",
) -> str:
    root = Path(root).resolve()
    paths = validate_patch(patch)
    current = _git(root, "branch", "--show-current").stdout.strip()
    if not current.startswith("builder/"):
        raise RuntimeError("Build Mode commit requires an active builder/* branch")
    diff = _git(root, "diff", "--", *paths)
    if diff.returncode or not diff.stdout.strip():
        raise RuntimeError("there is no applied Builder diff to commit")
    added = _git(root, "add", "--", *paths)
    if added.returncode:
        raise RuntimeError(added.stderr.strip() or "git add failed")
    subject = re.sub(r"\s+", " ", task).strip()[:68] or "Apply reviewed Builder change"
    commit = _git(root, "commit", "-m", subject)
    if commit.returncode:
        raise RuntimeError(commit.stderr.strip() or "git commit failed")
    builder_branch = current
    switched = _git(root, "switch", original_branch)
    if switched.returncode:
        raise RuntimeError(switched.stderr.strip() or "Could not restore original branch")
    merged = _git(root, "merge", "--ff-only", builder_branch)
    if merged.returncode:
        raise RuntimeError(merged.stderr.strip() or "Could not fast-forward tested Builder commit")
    _git(root, "branch", "-D", builder_branch)
    return commit.stdout.strip() + f"\nFast-forwarded into {original_branch}."


def discard_applied(
    root: str | Path,
    patch: str,
    original_branch: str,
    builder_branch: str,
) -> str:
    root = Path(root).resolve()
    validate_patch(patch)
    current = _git(root, "branch", "--show-current").stdout.strip()
    if current != builder_branch:
        raise RuntimeError("Builder branch is not active; refusing automatic discard")
    reversed_patch = _run(root, ["git", "apply", "-R", "-"], input_text=patch)
    if reversed_patch.returncode:
        raise RuntimeError("Could not reverse the Builder patch; inspect git diff")
    if not _clean_status(root):
        raise RuntimeError("Builder patch reversed but unrelated working-tree changes remain")
    switched = _git(root, "switch", original_branch)
    if switched.returncode:
        raise RuntimeError(switched.stderr.strip() or "Could not restore original branch")
    _git(root, "branch", "-D", builder_branch)
    return f"Discarded {builder_branch} and restored {original_branch}"
