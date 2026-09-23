from pathlib import Path
import subprocess

import pytest

from genesis import builder_engine, integrations
from genesis.builder_llm import LocalLLM
from genesis.builder_proposal import build_proposal, enforce_evidence_gate
from genesis.builder_repo_reader import RepoReader


PATCH = """diff --git a/example.py b/example.py
--- a/example.py
+++ b/example.py
@@ -1 +1 @@
-VALUE = 1
+VALUE = 2
"""


def _repo(tmp_path: Path, expected: int = 2) -> Path:
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "example.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "test_example.py").write_text(
        f"from example import VALUE\ndef test_value(): assert VALUE == {expected}\n",
        encoding="utf-8",
    )
    (tmp_path / ".gitignore").write_text("__pycache__/\n.pytest_cache/\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=tmp_path, check=True, capture_output=True)
    return tmp_path


def test_builder_llm_uses_dedicated_endpoint_without_starting_it():
    llm = LocalLLM()
    assert llm.base_url == integrations.BUILDER_URL
    assert llm.model == integrations.BUILDER_MODEL


def test_repo_reader_is_bounded_and_indexes_qml(tmp_path):
    (tmp_path / "Main.qml").write_text("Item { property string marker: \"FeeFee\" }\n")
    reader = RepoReader(tmp_path)
    assert any(path.suffix == ".qml" for path in reader.list_files())
    context = reader.search_context(["FeeFee"])
    assert "Main.qml" in context
    with pytest.raises(ValueError, match="outside"):
        reader.read_file(Path("/etc/passwd"))


def test_patch_validation_allows_qml_but_rejects_infrastructure_and_deletes():
    qml_patch = PATCH.replace("example.py", "genesis/qt_ui/Test.qml")
    assert builder_engine.validate_patch(qml_patch) == ("genesis/qt_ui/Test.qml",)
    with pytest.raises(ValueError, match="protected or external"):
        builder_engine.validate_patch(PATCH.replace("example.py", "../escape.py"))
    with pytest.raises(ValueError, match="protected infrastructure"):
        builder_engine.validate_patch(PATCH.replace("example.py", "systemd/unit.py"))
    with pytest.raises(ValueError, match="file deletion"):
        builder_engine.validate_patch(PATCH.replace("--- a/example.py", "deleted file mode 100644\n--- a/example.py"))


def test_failed_tests_rollback_and_restore_original_branch(tmp_path):
    root = _repo(tmp_path, expected=1)
    result = builder_engine.apply_and_test(root, PATCH)
    assert not result.tests_passed
    assert (root / "example.py").read_text() == "VALUE = 1\n"
    assert subprocess.run(
        ["git", "branch", "--show-current"], cwd=root, capture_output=True, text=True
    ).stdout.strip() == "main"
    assert not subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True
    ).stdout.strip()


def test_successful_patch_isolated_on_builder_branch_and_discardable(tmp_path):
    root = _repo(tmp_path, expected=2)
    result = builder_engine.apply_and_test(root, PATCH)
    assert result.tests_passed and result.applied
    assert result.original_branch == "main"
    assert result.builder_branch.startswith("builder/")
    assert (root / "example.py").read_text() == "VALUE = 2\n"
    message = builder_engine.discard_applied(
        root, PATCH, result.original_branch, result.builder_branch
    )
    assert "restored main" in message
    assert (root / "example.py").read_text() == "VALUE = 1\n"
    assert not subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True
    ).stdout.strip()


def test_proposal_uses_repository_evidence_and_gate():
    class Reader:
        def search_context(self, keywords, **options):
            assert "FeeFee" in keywords
            return "===== FILE: genesis/assistant_bridge.py =====\nclass AssistantBridge: pass"

    class LLM:
        def chat(self, system, user, max_tokens):
            assert "PROPOSE-ONLY MODE" in system
            assert "AssistantBridge" in user
            return "### PROPOSED CHANGE\nRepair the proven route."

    result = build_proposal("Repair FeeFee build route", reader=Reader(), llm=LLM())
    assert "Repair the proven route" in result
    rejected = enforce_evidence_gate(
        "There is no clear evidence of a problem.\n\n"
        "### PROPOSED CHANGE\nChange it anyway.\n\n"
        "### FILES THAT WOULD CHANGE\ngenesis/assistant_bridge.py"
    )
    proposed = rejected.split("### PROPOSED CHANGE", 1)[1].split(
        "### FILES THAT WOULD CHANGE", 1
    )[0]
    assert "Change it anyway" not in proposed


def test_proposal_has_change_distinguishes_none():
    from genesis.builder_proposal import proposal_has_change

    assert proposal_has_change(
        "### PROPOSED CHANGE\nFix route.\n\n### FILES THAT WOULD CHANGE\na.py"
    )
    assert not proposal_has_change(
        "### PROPOSED CHANGE\nNone.\n\n### FILES THAT WOULD CHANGE\na.py"
    )


def test_commit_fast_forwards_tested_builder_branch(tmp_path):
    root = _repo(tmp_path, expected=2)
    result = builder_engine.apply_and_test(root, PATCH)
    assert result.tests_passed
    output = builder_engine.commit_applied(
        root, PATCH, "Update example value", original_branch=result.original_branch
    )
    assert "Fast-forwarded into main" in output
    assert subprocess.run(
        ["git", "branch", "--show-current"], cwd=root, capture_output=True, text=True
    ).stdout.strip() == "main"
    assert (root / "example.py").read_text() == "VALUE = 2\n"
    branches = subprocess.run(
        ["git", "branch", "--format=%(refname:short)"],
        cwd=root, capture_output=True, text=True
    ).stdout.splitlines()
    assert all(not branch.startswith("builder/") for branch in branches)


def test_builder_service_contract_is_on_demand_and_aliased():
    root = Path(__file__).resolve().parents[1]
    unit = (root / "systemd" / "genesis-builder.service").read_text()
    assert "--alias genesis-builder" in unit
    assert "--port 8080" in unit
    assert "--ctx-size 16384" in unit
    assert "ExecStartPre=/bin/sleep 10" in unit
