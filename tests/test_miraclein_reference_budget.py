"""Offline reference-budget contract: no network, GPU loading, or generation."""
import copy
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from PyQt6.QtCore import QCoreApplication

import qt_cockpit as c
from genesis.backend_routing import Route, use_route


BUDGET = (640 / 1024) ** 2


@pytest.fixture
def catalog():
    return json.loads((Path(__file__).parent / "fixtures/runpod_stage_models_schema.json").read_text())


def advanced_args(prompt="one", seed=111):
    return (prompt, "", 640, 640, c.LOCAL_MIRACLEIN_9B_MODEL,
            "None", "None", "file:///tmp/source.png", "file:///tmp/pose.png",
            False, False, False, 12, 1.0, seed, 1.0, "euler", "Flux2Scheduler",
            "None", 0.0, 0.0, 0.0)


def test_only_local_miraclein_source_fast_requests_smaller_reference():
    for model in c.SUPPORTED_CREATE_MODELS:
        for remote in (False, True):
            profile = c.model_profile_settings(model, remote=remote)
            for group in ("qualityPresets", "sourceQualityPresets", "createQualityPresets"):
                for name, preset in profile[group].items():
                    if model == c.LOCAL_MIRACLEIN_9B_MODEL and not remote and group == "sourceQualityPresets" and name == "Fast":
                        assert preset["referenceMegapixels"] == BUDGET
                        assert preset["cfg"] == 1.0
                        assert (preset["width"], preset["height"]) == (640, 640)
                    else:
                        assert "referenceMegapixels" not in preset, (model, remote, group, name)


@pytest.mark.parametrize("value,expected", [
    (BUDGET, BUDGET), (1.0, 1.0), (0.0, 0.0), (-0.1, 0.0),
    (1.01, 0.0), (float("nan"), 0.0), (float("inf"), 0.0),
])
def test_reference_budget_setter_keeps_safe_range(value, expected):
    bridge = c.GenerationBridge()
    assert bridge._source_reference_megapixels == 0.0
    bridge.setSourceReferenceMegapixels(value)
    assert bridge._source_reference_megapixels == expected


def test_advanced_request_captures_reference_budget_before_worker(monkeypatch):
    bridge = c.GenerationBridge()
    snapshots = []
    dispatch = Mock(side_effect=lambda *args: snapshots.append(dict(bridge._next_generation_controls)))
    monkeypatch.setattr(bridge, "queueGenerate", dispatch)
    bridge.setSourceReferenceMegapixels(BUDGET)
    bridge.queueGenerateAdvanced(*advanced_args())
    assert len(snapshots) == 1
    controls = snapshots[0]
    # Transient controls are only valid during synchronous job preparation.
    assert bridge._next_generation_controls is None
    bridge.setSourceReferenceMegapixels(0.0)
    assert controls["source_reference_megapixels"] == BUDGET
    assert controls["width"] == controls["height"] == 640
    assert controls["cfg"] == 1.0
    dispatch.assert_called_once()


def test_waiting_jobs_keep_their_reference_budget(monkeypatch):
    app = QCoreApplication.instance() or QCoreApplication([])
    bridge = c.GenerationBridge()
    runs = []

    def capture(*args):
        runs.append((args[0], bridge._source_reference_megapixels))
        bridge._set_busy(True)

    monkeypatch.setattr(bridge, "queueGenerateAdvanced", capture)
    bridge.setSourceReferenceMegapixels(BUDGET)
    bridge.enqueueGenerateAdvanced(*advanced_args("first"))
    bridge.setSourceReferenceMegapixels(0.0)
    bridge.enqueueGenerateAdvanced(*advanced_args("second"))
    bridge.setSourceReferenceMegapixels(BUDGET)
    bridge.enqueueGenerateAdvanced(*advanced_args("third"))
    bridge.setSourceReferenceMegapixels(0.0)
    assert runs == [("first", BUDGET)]
    assert [job["source_reference_megapixels"] for job in bridge._pending_generations] == [0.0, BUDGET]
    bridge._set_busy(False)
    app.processEvents()
    assert runs == [("first", BUDGET), ("second", 0.0)]
    bridge._set_busy(False)
    app.processEvents()
    assert runs == [("first", BUDGET), ("second", 0.0), ("third", BUDGET)]
    assert not bridge.pendingGenerations


def captured_reference(monkeypatch, tmp_path, catalog, *, budget=None,
                       workflow=None, model=None, destination="LOCAL", pose=True):
    bridge = c.GenerationBridge()
    source = tmp_path / "source.png"
    secondary = tmp_path / "pose.png"
    source.write_bytes(b"original source remains untouched")
    secondary.write_bytes(b"original pose remains untouched")
    client = Mock()
    client.upload_image.side_effect = lambda path: {"name": path.name, "subfolder": "bench"}
    submit = Mock(return_value=tmp_path / "out.png")
    monkeypatch.setattr(bridge, "_submit_and_save", submit)
    controls = dict(width=640, height=640, steps=12, cfg=1.0, seed=123)
    if budget is not None:
        controls["source_reference_megapixels"] = budget
    route = Route(destination, "https://test-8189.proxy.runpod.net" if destination == "RUNPOD" else "")
    with use_route(route):
        bridge._run_reference_stage(client, catalog, workflow or c.REMOTE_MIRACLEIN_EDIT_WORKFLOW,
                                    source, "A ceramic vase beside a window", "stamp", "Stage1",
                                    secondary_image=secondary if pose else None,
                                    controls=controls, model_override=model or c.LOCAL_MIRACLEIN_9B_MODEL)
    assert source.read_bytes() == b"original source remains untouched"
    assert secondary.read_bytes() == b"original pose remains untouched"
    client.submit.assert_not_called()
    assert submit.call_count == 1
    return copy.deepcopy(submit.call_args.args[1]), client


@pytest.mark.parametrize("pose", [False, True])
def test_local_fast_changes_only_primary_reference_budget(monkeypatch, tmp_path, catalog, pose):
    baseline, _ = captured_reference(monkeypatch, tmp_path, catalog, pose=pose)
    fast, client = captured_reference(monkeypatch, tmp_path, catalog, budget=BUDGET, pose=pose)
    assert baseline["12"]["inputs"]["megapixels"] == 1
    assert fast["12"]["inputs"]["megapixels"] == BUDGET
    assert fast["12"]["inputs"]["image"] == ["10", 0]
    assert fast["15"]["inputs"]["pixels"] == ["12", 0]
    assert fast["17"]["inputs"]["latent"] == ["15", 0]
    assert fast["18"]["inputs"]["latent"] == ["15", 0]
    if pose:
        assert client.upload_image.call_count == 2
        assert fast["17"]["inputs"]["conditioning"] == ["__genesis_pose_positive__", 0]
        assert fast["18"]["inputs"]["conditioning"] == ["__genesis_pose_negative__", 0]
        assert fast["__genesis_pose_encode__"]["inputs"]["pixels"] == ["__genesis_pose__", 0]
    else:
        assert client.upload_image.call_count == 1
    fast["12"]["inputs"]["megapixels"] = baseline["12"]["inputs"]["megapixels"]
    assert fast == baseline


@pytest.mark.parametrize("kwargs", [
    {"destination": "RUNPOD"},
    {"model": c.REMOTE_AISHA_9B_MODEL},
    {"workflow": c.REMOTE_KLEIN9B_WORKFLOW},
])
def test_reference_budget_does_not_change_other_routes(monkeypatch, tmp_path, catalog, kwargs):
    baseline, _ = captured_reference(monkeypatch, tmp_path, catalog, **kwargs)
    with_budget, _ = captured_reference(monkeypatch, tmp_path, catalog, budget=BUDGET, **kwargs)
    assert with_budget == baseline


@pytest.mark.parametrize("budget", [0.0, -0.1, 1.01, float("nan"), float("inf")])
def test_invalid_budget_does_not_change_saved_graph(monkeypatch, tmp_path, catalog, budget):
    baseline, _ = captured_reference(monkeypatch, tmp_path, catalog)
    invalid, _ = captured_reference(monkeypatch, tmp_path, catalog, budget=budget)
    assert invalid == baseline


@pytest.mark.parametrize("broken", ["missing_scaler", "wrong_class", "wrong_source", "bypassed_scaler"])
def test_changed_primary_reference_topology_fails_before_upload(monkeypatch, tmp_path, catalog, broken):
    graph = c.workflow_lab.workflow_to_prompt(c.REMOTE_MIRACLEIN_EDIT_WORKFLOW, catalog)
    if broken == "missing_scaler":
        graph.pop("12")
    elif broken == "wrong_class":
        graph["12"]["class_type"] = "ImageScale"
    elif broken == "wrong_source":
        graph["12"]["inputs"]["image"] = ["3", 0]
    else:
        graph["15"]["inputs"]["pixels"] = ["10", 0]
    monkeypatch.setattr(c.workflow_lab, "workflow_to_prompt", lambda *args: copy.deepcopy(graph))
    bridge = c.GenerationBridge()
    submit = Mock()
    monkeypatch.setattr(bridge, "_submit_and_save", submit)
    client = Mock()
    with use_route(Route("LOCAL", "")), pytest.raises(c.workflow_lab.ComfyError):
        bridge._run_reference_stage(client, catalog, c.REMOTE_MIRACLEIN_EDIT_WORKFLOW,
                                    tmp_path / "source.png", "A ceramic vase", "stamp", "Stage1",
                                    secondary_image=tmp_path / "pose.png",
                                    controls={"source_reference_megapixels": BUDGET},
                                    model_override=c.LOCAL_MIRACLEIN_9B_MODEL)
    client.upload_image.assert_not_called()
    submit.assert_not_called()
