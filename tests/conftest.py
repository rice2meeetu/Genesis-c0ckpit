import sys

import pytest


LINUX_ONLY_TESTS = {
    "test_workbench_consumes_pose_and_source_roles_without_touching_stage_outputs",
}


def pytest_collection_modifyitems(items):
    """Skip tests that require the separate legacy Linux Pose Maker on Windows."""
    if sys.platform != "win32":
        return
    marker = pytest.mark.skip(
        reason="Legacy Linux Pose Maker integration is not present in the Windows build."
    )
    for item in items:
        if item.name in LINUX_ONLY_TESTS:
            item.add_marker(marker)
