"""Neutral, isolated regression checks for the focused Cockpit repairs.

The tests execute selected methods from ``main.py`` without constructing the
Tk application, starting services, opening user images, or importing the
module-level settings code.
"""

from __future__ import annotations

import ast
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from genesis.thumbnails import generate_thumbnail


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = PROJECT_ROOT / "main.py"


def cockpit_method(name: str, **extra_globals):
    """Compile one current PhotoStudio method without launching the app."""
    tree = ast.parse(MAIN_PATH.read_text(encoding="utf-8"))
    photo_studio = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "PhotoStudio"
    )
    method = next(
        node
        for node in photo_studio.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )
    namespace = {"Path": Path, **extra_globals}
    exec(compile(ast.Module([method], type_ignores=[]), str(MAIN_PATH), "exec"), namespace)
    return namespace[name]


class Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class PackedWidget:
    def __init__(self, packed=True):
        self.manager = "pack" if packed else ""
        self.children = []

    def winfo_manager(self):
        return self.manager

    def pack_info(self):
        return {"fill": "x", "padx": 3}

    def pack_forget(self):
        self.manager = ""

    def pack(self, **_options):
        self.manager = "pack"

    def winfo_children(self):
        return list(self.children)

    def destroy(self):
        pass

    def yview_moveto(self, _position):
        pass


class CockpitRepairTests(unittest.TestCase):
    def test_camera_ui_has_no_automatic_service_stop(self):
        tree = ast.parse(MAIN_PATH.read_text(encoding="utf-8"))
        camera_method = next(
            node
            for class_node in tree.body
            if isinstance(class_node, ast.ClassDef) and class_node.name == "PhotoStudio"
            for node in class_node.body
            if isinstance(node, ast.FunctionDef) and node.name == "_camera_ui"
        )
        scheduled_stops = [
            node
            for node in ast.walk(camera_method)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "after"
            and any("stop_cameras" in ast.unparse(argument) for argument in node.args)
        ]
        self.assertEqual(scheduled_stops, [])

    def test_ambiguous_model_and_lora_slots_are_preserved(self):
        owner = types.SimpleNamespace(
            gen_cfg_var=Value(3.5),
            gen_steps_var=Value(20),
            gen_seed_var=Value(1),
            gen_width_var=Value(768),
            gen_height_var=Value(768),
            gen_denoise_var=Value(0.8),
        )
        prompt = {
            "model-a": {"class_type": "UNETLoader", "inputs": {"unet_name": "a"}},
            "model-b": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "b"}},
            "lora-a": {"class_type": "LoraLoader", "inputs": {"lora_name": "la"}},
            "lora-b": {"class_type": "LoraLoader", "inputs": {"lora_name": "lb"}},
            "stage-a": {"class_type": "KSampler", "inputs": {"steps": 10}},
            "stage-b": {"class_type": "KSampler", "inputs": {"steps": 30}},
        }
        method = cockpit_method("_generation_overrides")

        defaults = method(owner, prompt, None, "", "Use workflow default", "Use workflow default")
        self.assertNotIn("model-a", defaults)
        self.assertNotIn("model-b", defaults)
        self.assertNotIn("lora-a", defaults)
        self.assertNotIn("lora-b", defaults)
        self.assertNotIn("stage-a", defaults)
        self.assertNotIn("stage-b", defaults)

        with self.assertRaisesRegex(ValueError, "Model selection needs exactly one workflow slot"):
            method(owner, prompt, None, "", "replacement", "Use workflow default")
        with self.assertRaisesRegex(ValueError, "LoRA selection needs exactly one workflow slot"):
            method(owner, prompt, None, "", "Use workflow default", "replacement")

    def test_unique_model_and_lora_slots_can_still_be_overridden(self):
        owner = types.SimpleNamespace()
        prompt = {
            "model": {"class_type": "UNETLoader", "inputs": {"unet_name": "old-model"}},
            "lora": {"class_type": "LoraLoader", "inputs": {"lora_name": "old-lora"}},
        }
        overrides = cockpit_method("_generation_overrides")(
            owner, prompt, None, "", "new-model", "new-lora"
        )
        self.assertEqual(overrides["model"]["unet_name"], "new-model")
        self.assertEqual(overrides["lora"]["lora_name"], "new-lora")

    def test_edit_result_routes_to_actual_editor(self):
        source = MAIN_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        finished = next(
            node
            for class_node in tree.body
            if isinstance(class_node, ast.ClassDef) and class_node.name == "PhotoStudio"
            for node in class_node.body
            if isinstance(node, ast.FunctionDef) and node.name == "_generation_finished"
        )
        edit_button = next(
            node
            for node in ast.walk(finished)
            if isinstance(node, ast.Call)
            and any(
                keyword.arg == "text"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value == "EDIT IMAGE"
                for keyword in node.keywords
            )
        )
        command = next(keyword.value for keyword in edit_button.keywords if keyword.arg == "command")
        self.assertIn("open_image_editor", ast.unparse(command))
        self.assertNotIn("_preview_path", ast.unparse(command))

    def test_repeated_prompt_studio_entry_restores_main_controls(self):
        normal = PackedWidget()
        host = PackedWidget(packed=False)
        outer = types.SimpleNamespace(winfo_children=lambda: [normal, host])
        owner = types.SimpleNamespace(
            ai_main_container=outer,
            ai_prompt_host=host,
            ai_canvas=PackedWidget(),
            status=types.SimpleNamespace(config=lambda **_options: None),
            _show_ai_main=lambda: None,
        )
        enter = cockpit_method("_show_ai_prompt_studio")
        leave = cockpit_method("_show_ai_main")

        with patch("genesis.prompt_manager.build_prompt_manager", return_value=object()):
            enter(owner)
            enter(owner)
            leave(owner)

        self.assertEqual(normal.manager, "pack")
        self.assertEqual(owner._ai_saved_pack, [])

    def test_folder_refresh_remains_recursive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "nested"
            nested.mkdir()
            (root / "top.png").touch()
            (nested / "inside.png").touch()
            owner = types.SimpleNamespace(
                _remember_photo_project=lambda _path: None,
                _populate_file_checks=lambda: None,
                status=types.SimpleNamespace(config=lambda **_options: None),
            )
            cockpit_method("scan_folder_again", SUPPORTED={".png"})(owner, root)
            self.assertEqual(set(owner.files), {root / "top.png", nested / "inside.png"})

    def test_thumbnail_changes_when_source_revision_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            cache = root / "cache"
            Image.new("RGB", (12, 10), "blue").save(source)
            first = generate_thumbnail(source, cache)
            first_bytes = first.read_bytes()

            Image.new("RGB", (24, 18), "red").save(source)
            second = generate_thumbnail(source, cache)

            self.assertNotEqual(first, second)
            self.assertNotEqual(first_bytes, second.read_bytes())

    def test_pose_handoff_requires_an_explicit_supported_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            reference = Path(directory) / "neutral-reference.png"
            reference.touch()
            statuses = []
            queued = []
            opened = []
            owner = types.SimpleNamespace(
                status=types.SimpleNamespace(
                    configure=lambda **options: statuses.append(options.get("text"))
                ),
                open_image_editor=lambda _path: None,
                open_legacy_pose_workbench=lambda: opened.append(True),
            )
            method = cockpit_method(
                "_send_native_pose_reference",
                queue_pose_workbench_handoff=lambda path, role: queued.append((path, role)),
            )

            method(owner, {"file": reference}, "pose_reference")
            method(owner, {"file": reference}, "source_image")

            self.assertEqual(
                queued,
                [(reference, "pose_reference"), (reference, "source_image")],
            )
            self.assertEqual(opened, [True, True])
            self.assertIn("Source Image handoff queued", statuses[-1])
            with self.assertRaisesRegex(ValueError, "Unsupported Pose handoff destination"):
                method(owner, {"file": reference}, "stage_1")

    def test_pose_menu_exposes_only_approved_roles(self):
        from genesis.pose_library import POSE_SEND_DESTINATIONS

        self.assertEqual(
            [(destination.key, destination.label) for destination in POSE_SEND_DESTINATIONS],
            [
                ("pose_reference", "Send as Pose Reference"),
                ("source_image", "Send as Source Image"),
                ("viewer_editor", "Open in Viewer / Editor"),
            ],
        )

    def test_workbench_consumes_pose_and_source_roles_without_touching_stage_outputs(self):
        pose_app = Path("/home/rice2meetyou/AI/GENESIS_POSE_MAKER/app.py")
        tree = ast.parse(pose_app.read_text(encoding="utf-8"))
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "consume_pose_workbench_handoff"
        )
        namespace = {
            "Path": Path,
            "json": __import__("json"),
            "POSE_WORKBENCH_HANDOFF_FILE": Path("unused-test-handoff.json"),
        }
        exec(compile(ast.Module([function], type_ignores=[]), str(pose_app), "exec"), namespace)
        consume = namespace["consume_pose_workbench_handoff"]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "neutral-reference.png"
            reference.touch()
            handoff = root / "handoff.json"
            handoff.write_text(
                '{"version": 1, "role": "pose_reference", "path": "'
                + str(reference)
                + '"}',
                encoding="utf-8",
            )
            result = consume("existing-source", "existing-pose", "photo", handoff)
            self.assertEqual(result[:3], ("existing-source", str(reference), "skeleton"))
            self.assertFalse(handoff.exists())

            handoff.write_text(
                '{"version": 1, "role": "source_image", "path": "'
                + str(reference)
                + '"}',
                encoding="utf-8",
            )
            result = consume("existing-source", "existing-pose", "photo", handoff)
            self.assertEqual(result[:3], (str(reference), "existing-pose", "photo"))
            self.assertFalse(handoff.exists())


if __name__ == "__main__":
    unittest.main()
