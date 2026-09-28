"""The v1 checkpoint's pose task must be selected without mutating its input."""

import importlib.util
from pathlib import Path


class FakeControlNet:
    def __init__(self, args=None):
        self.args = dict(args or {})

    def copy(self):
        return FakeControlNet(self.args)

    def set_extra_arg(self, name, value):
        self.args[name] = value


def test_union_pro_v1_pose_mode():
    path = Path(__file__).resolve().parents[1] / "comfy_nodes/genesis_union_pose/__init__.py"
    spec = importlib.util.spec_from_file_location("genesis_union_pose", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = FakeControlNet({"control_type": [0]})
    result, = module.GenesisFluxUnionProPose().select_pose(original)
    assert result is not original
    assert result.args["control_type"] == [4]
    assert original.args["control_type"] == [0]
