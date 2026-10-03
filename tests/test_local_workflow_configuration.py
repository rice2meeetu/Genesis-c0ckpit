from unittest.mock import Mock
from PyQt6.QtCore import QUrl
import qt_cockpit as c
from genesis.backend_routing import Route, use_route


def test_local_qwen_selection_reaches_worker(monkeypatch, tmp_path):
    source = tmp_path / "source.png"
    source.write_bytes(b"source")
    bridge = c.GenerationBridge()
    thread = Mock()
    monkeypatch.setattr(c.threading, "Thread", thread)
    bridge.queueGenerate("a landscape", "", 512, 512, c.QWEN_MODEL,
                         "None", "None", "None", 0, 0, 0,
                         QUrl.fromLocalFile(str(source)).toString(), "",
                         False, False, False)
    thread.return_value.start.assert_called_once()
    assert thread.call_args.kwargs["args"][5] == c.QWEN_MODEL


def test_missing_refinement_is_rejected_before_stage_one(monkeypatch, tmp_path):
    bridge = c.GenerationBridge()
    monkeypatch.setattr(bridge, "_connect_comfyui", lambda: (Mock(), {}))
    def reject(workflow, info, model_override=None):
        if workflow == c.STAGE_2_WORKFLOW:
            raise c.workflow_lab.ComfyError("Lustify checkpoint missing")
    monkeypatch.setattr(c, "validate_remote_workflow_assets", reject)
    run = Mock()
    monkeypatch.setattr(bridge, "_run_reference_stage", run)
    statuses = []
    monkeypatch.setattr(bridge, "_set_status", statuses.append)
    with use_route(Route("LOCAL", "")):
        bridge._run_generate("a landscape", "", 512, 512, c.QWEN_MODEL,
                             "None", "None", "None", 0, 0, 0,
                             tmp_path / "source.png", None, True, False, False)
    run.assert_not_called()
    assert "Lustify checkpoint missing" in statuses[-1]
