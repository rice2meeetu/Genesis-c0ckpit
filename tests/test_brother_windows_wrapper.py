from pathlib import Path

import qt_cockpit
import qt_cockpit_brother_windows as wrapper


def test_wrapper_qml_is_windows_standalone_shell():
    qml = Path("genesis/qt_ui/MainPremiumWindows.qml").read_text(encoding="utf-8")
    assert "Brother Standalone Image Wrapper" in qml
    assert "GENESIS WINDOWS · STANDALONE" in qml
    assert 'label:"Grok Imagine"' not in qml
    assert "appRoot.pageIndex = 12" not in qml
    assert 'label:"Image Generation", page:0' in qml


def test_wrapper_page_map_keeps_create_and_face_swap():
    assert wrapper.PAGE_INDEXES["create"] == 0
    assert wrapper.PAGE_INDEXES["face-swap"] == 11


def test_live_catalog_rows_can_be_marked_local():
    info = {
        "UNETLoader": {
            "input": {
                "required": {
                    "unet_name": [[qt_cockpit.REMOTE_KLEIN_9B_MODEL], {}],
                }
            }
        }
    }
    rows = qt_cockpit.build_remote_generation_profiles(info, remote=False)
    assert len(rows) == 1
    assert rows[0]["model"] == qt_cockpit.REMOTE_KLEIN_9B_MODEL
    assert rows[0]["remote"] is False
    assert rows[0]["runnable"] is True
