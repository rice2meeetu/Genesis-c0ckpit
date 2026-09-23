from pathlib import Path
from PyQt6.QtCore import QCoreApplication
from genesis.media_bridge import MediaBridge

app = QCoreApplication.instance() or QCoreApplication([])

def test_set_duplicates_and_faces_updates_review():
    bridge = MediaBridge()
    bridge._set_duplicates({"exact_groups":[["/a","/b"]],"near_pairs":[{"left":"/c","right":"/d","distance":2}]})
    assert len(bridge.duplicatePairs) == 2
    assert bridge.faceGroups == []
    bridge._set_faces([{"group_id":1,"count":1,"members":[{"path":"/x"}]}])
    assert bridge.duplicatePairs == []
    assert len(bridge.faceGroups) == 1

def test_open_result_folder_no_result_is_safe():
    bridge = MediaBridge()
    bridge.openResultFolder()
    assert bridge.status == "No saved result yet"
