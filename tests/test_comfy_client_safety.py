from unittest.mock import patch

from genesis.comfy_client import ComfyClient


def test_wait_interrupts_and_deletes_prompt_when_abort_check_trips():
    client = ComfyClient()
    reason = "GPU safety latch: reboot required after KFD/SVM warning"
    with patch.object(client, "interrupt") as interrupt, patch.object(client, "cancel") as cancel:
        result = client.wait(
            "prompt-123",
            abort_check=lambda: reason,
            poll_interval=0.01,
            timeout=1,
        )
    assert result.status == "interrupted"
    assert result.error == reason
    interrupt.assert_called_once_with()
    cancel.assert_called_once_with(["prompt-123"])


def test_wait_does_not_touch_abort_endpoints_when_check_is_clean():
    client = ComfyClient()
    with patch.object(client, "history", return_value={
        "prompt-123": {"status": {"completed": True}, "outputs": {}}
    }), patch.object(client, "interrupt") as interrupt, patch.object(client, "cancel") as cancel:
        result = client.wait("prompt-123", abort_check=lambda: None, timeout=1)
    assert result.status == "completed"
    interrupt.assert_not_called()
    cancel.assert_not_called()
