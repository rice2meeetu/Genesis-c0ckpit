from pathlib import Path


def test_cancel_tracks_client_and_prompt_and_interrupts_both_running_and_pending():
    text = Path('qt_cockpit.py').read_text()
    assert 'self._active_client = None' in text
    assert 'self._active_prompt_id = None' in text
    assert 'self._active_prompt_id = prompt_id' in text
    cancel = text[text.index('    def cancelGeneration'):text.index('    def _abort_reason')]
    assert 'client.interrupt()' in cancel
    assert 'client.cancel([prompt_id])' in cancel
