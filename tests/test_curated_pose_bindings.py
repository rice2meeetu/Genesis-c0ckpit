"""Curated presets bind only their declared, indexed skeleton files."""
import json
from pathlib import Path

import pytest

import qt_cockpit as c


@pytest.fixture
def curated_library(monkeypatch, tmp_path):
    project = tmp_path / "project"
    library = project / "genesis/reference/assets/pose_library"
    library.mkdir(parents=True)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(c, "PROJECT_ROOT", project)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    def pose(relative_path, *, exists=True):
        path = library / relative_path
        if exists:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        return {"source": path.as_uri(), "thumbnail": path.as_uri(),
                "poseId": relative_path.removesuffix("_bone_structure.png"),
                "name": "Unrelated skeleton label", "category": "Lying",
                "prompt": "Skeleton fallback text must not replace the preset",
                "sourceMetadata": {"prompt": "Skeleton metadata"}}

    def load(declared, poses):
        row = {"id": "authored-preset", "name": "Authored pose", "priority": 3,
               "prompt": "The authored pose composition.", "skeletons": declared,
               "sourceMetadata": {"model_prompts": {"sdxl": "Authored SDXL wording"}}}
        (home / "GENESIS_CURATED_PRESETS_DATABASE.json").write_text(
            json.dumps({"sexual_act_presets": [row]}), encoding="utf-8")
        presets = c.load_curated_pose_presets(pose_rows=poses)
        return next(preset for preset in presets if preset["collection"] == "Curated 18")

    return library, pose, load


def test_curated_uses_first_declared_existing_indexed_skeleton(curated_library):
    _, pose, load = curated_library
    first = pose("lying/768512/first_bone_structure.png")
    second = pose("lying/768512/second_bone_structure.png")
    declared = ["lying/missing.png", "lying/768512/first_bone_structure.png",
                "lying/768512/second_bone_structure.png"]

    preset = load(declared, [second, first])

    assert preset["source"] == first["source"]
    assert preset["thumbnail"] == first["thumbnail"]
    assert preset["poseId"] == first["poseId"]
    assert preset["poseHintCategory"] == "Lying"
    assert preset["requiresPoseSelection"] is False
    assert preset["skeletons"] == declared
    assert preset["id"] == "curated18:authored-preset"
    assert preset["name"] == "Authored pose"
    assert preset["label"] == "Authored pose · Curated 18"
    assert preset["prompt"] == "The authored pose composition."
    assert preset["sourceMetadata"] == {
        "model_prompts": {"sdxl": "Authored SDXL wording"}}


def test_curated_skips_unindexed_and_missing_declared_files(curated_library):
    _, pose, load = curated_library
    pose("lying/768512/unindexed_bone_structure.png")
    missing = pose("lying/768512/missing_bone_structure.png", exists=False)
    indexed = pose("lying/768512/indexed_bone_structure.png")

    preset = load(["lying/768512/unindexed_bone_structure.png",
                   "lying/768512/missing_bone_structure.png",
                   "lying/768512/indexed_bone_structure.png"], [missing, indexed])

    assert preset["source"] == indexed["source"]
    assert preset["requiresPoseSelection"] is False


@pytest.mark.parametrize("poses", [None, []])
def test_curated_without_index_requires_explicit_pose_selection(curated_library, poses):
    _, pose, load = curated_library
    pose("lying/768512/declared_bone_structure.png")

    preset = load(["lying/768512/declared_bone_structure.png"], poses)

    assert preset["requiresPoseSelection"] is True
    assert "source" not in preset
    assert "poseId" not in preset


def test_curated_never_guesses_from_a_matching_basename(curated_library):
    _, pose, load = curated_library
    other = pose("standing/512768/same_bone_structure.png")

    preset = load(["lying/768512/same_bone_structure.png"], [other])

    assert preset["requiresPoseSelection"] is True
    assert "source" not in preset


def test_curated_rejects_paths_outside_bundled_library(curated_library):
    library, _, load = curated_library
    outside = library.parent / "outside.png"
    outside.touch()
    indexed = {"source": outside.as_uri(), "poseId": "outside"}

    preset = load([str(outside), "../outside.png", None, {"source": "outside.png"}], [indexed])

    assert preset["requiresPoseSelection"] is True
    assert "source" not in preset


@pytest.mark.parametrize("declared", [None, "lying/768512/skeleton.png", {"path": "skeleton.png"}])
def test_curated_invalid_declaration_requires_selection(curated_library, declared):
    _, _, load = curated_library

    preset = load(declared, [])

    assert preset["requiresPoseSelection"] is True
    assert preset["skeletons"] == []
    assert "source" not in preset
