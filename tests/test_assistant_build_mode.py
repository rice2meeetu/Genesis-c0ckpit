from pathlib import Path

from genesis import builder_engine, builder_proposal
from genesis.assistant_bridge import AssistantBridge


def _proposal(change: str = "Repair the proven route.") -> str:
    return (
        "### TASK UNDERSTANDING\nFix Build Mode.\n\n"
        "### CONFIRMED RELEVANT CODE\nAssistantBridge exists.\n\n"
        f"### PROPOSED CHANGE\n{change}\n\n"
        "### FILES THAT WOULD CHANGE\ngenesis/assistant_bridge.py\n"
    )


def test_build_chat_returns_evidence_gated_proposal(monkeypatch):
    monkeypatch.setenv("GENESIS_AI_PAUSED", "0")
    monkeypatch.setattr(builder_proposal, "build_proposal", lambda task: _proposal())
    bridge = AssistantBridge()
    bridge._mode = "BUILD"
    bridge._build_task = "Fix Build Mode"
    bridge._set_busy(True)

    bridge._run_chat()

    assert bridge.buildState == "PROPOSAL_READY"
    assert bridge.buildCanDraft
    assert "PROPOSED CHANGE" in bridge.messages[-1]["content"]
    assert not bridge.busy


def test_build_chat_refuses_to_offer_patch_without_proven_change(monkeypatch):
    monkeypatch.setenv("GENESIS_AI_PAUSED", "0")
    monkeypatch.setattr(builder_proposal, "build_proposal", lambda task: _proposal("None."))
    bridge = AssistantBridge()
    bridge._mode = "BUILD"
    bridge._build_task = "Maybe change something"
    bridge._set_busy(True)

    bridge._run_chat()

    assert bridge.buildState == "IDLE"
    assert not bridge.buildCanDraft


def test_build_patch_review_apply_and_commit_state_machine(monkeypatch):
    monkeypatch.setenv("GENESIS_AI_PAUSED", "0")
    bridge = AssistantBridge()
    bridge._mode = "BUILD"
    bridge._build_task = "Fix proven issue"
    bridge._build_proposal = _proposal()
    bridge._set_build_state("PROPOSAL_READY")
    monkeypatch.setattr(builder_engine, "draft_change", lambda *args, **kwargs: "diff --git a/a.py b/a.py\n")

    bridge._run_build_draft()
    assert bridge.buildState == "PATCH_READY"
    assert bridge.buildCanApply

    passed = builder_engine.ApplyResult(True, True, "140 passed", "main", "builder/test")
    monkeypatch.setattr(builder_engine, "apply_and_test", lambda *args, **kwargs: passed)
    bridge._run_build_apply()
    assert bridge.buildState == "APPLIED_TESTED"
    assert bridge.buildCanCommit

    monkeypatch.setattr(
        builder_engine, "commit_applied",
        lambda *args, **kwargs: "commit ok\nFast-forwarded into main.",
    )
    bridge._run_build_commit()
    assert bridge.buildState == "COMMITTED"
    assert not bridge.buildCanCommit
    assert "BUILD COMMITTED" in bridge.messages[-1]["content"]


def test_ai_pause_requires_explicit_user_toggle(monkeypatch):
    monkeypatch.delenv("GENESIS_AI_PAUSED", raising=False)
    bridge = AssistantBridge()
    assert bridge.inferencePaused is True

    bridge.setInferencePaused(False)

    assert bridge.inferencePaused is False
    assert "safety-gated" in bridge.status


def test_feefee_qml_exposes_review_controls_and_pause_toggle():
    root = Path(__file__).resolve().parents[1]
    qml = (root / "genesis" / "qt_ui" / "FeeFeeChat.qml").read_text()
    assert 'text: "Draft Patch"' in qml
    assert 'text: "Apply + Test"' in qml
    assert 'text: "Commit"' in qml
    assert 'text: "Discard"' in qml
    assert "buildCanDraft" in qml and "buildCanApply" in qml
    assert "setInferencePaused" in qml
