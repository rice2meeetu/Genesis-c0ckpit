from pathlib import Path


def test_reactor_restore_model_matches_node_schema():
    source = Path("genesis/reference/pose_maker_app.py").read_text()
    assert "codeformer-v0.1.0.pth" in source
    assert "{\"\", \"codeformer\", \"codeformer-v0.1.0.pth\"}" in source
    assert "restore_model = gr.Textbox(value=\"codeformer-v0.1.0.pth\"" in source
