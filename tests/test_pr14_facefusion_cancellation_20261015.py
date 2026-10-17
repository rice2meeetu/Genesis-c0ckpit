"""Local FaceFusion cancel must end only its own process and never adopt result.

Uses temporary synthetic files and an unrelated sleeping Python subprocess;
no local FaceFusion installation, personal photos, GPU, or RunPod calls.
"""
from pathlib import Path
from types import SimpleNamespace
from threading import Event, Thread
from unittest.mock import Mock
import subprocess
import sys
import time

import pytest
from PIL import Image
from PyQt6.QtCore import QCoreApplication

import qt_cockpit as c
from genesis.backend_routing import Route, use_route
from genesis import integrations


def bridge(tmp_path):
    QCoreApplication.instance() or QCoreApplication([])
    b=c.GenerationBridge()
    b._output_dir=tmp_path/'output'
    b._facefusion_provider='cpu'
    return b


def image(path, color='blue'):
    Image.new('RGB',(40,40),color).save(path)
    return path


def test_cancel_during_manual_facefusion_never_adopts_even_a_saved_output(tmp_path,monkeypatch):
    b=bridge(tmp_path)
    source=image(tmp_path/'source.png')
    target=image(tmp_path/'target.png')
    original=target.read_bytes()
    b._set_busy(True)
    adopted=Mock()
    finished=Mock()
    monkeypatch.setattr(b,'_adopt_operation_result',adopted)
    monkeypatch.setattr(b,'_record_finish',finished)
    def simulate_late_success(cmd,**kwargs):
        # Test cancellation exactly when the external process returns, where
        # the old implementation incorrectly reported a successful FaceFusion.
        b.cancelGeneration()
        image(Path(cmd[cmd.index('--output-path')+1]),'black')
        return SimpleNamespace(returncode=0,stdout='late success')
    monkeypatch.setattr(b,'_run_local_facefusion_command',simulate_late_success)
    b._run_facefusion(target,source,tmp_path/'python',tmp_path/'facefusion.py',tmp_path/'facefusion.ini')
    adopted.assert_not_called()
    finished.assert_not_called()
    assert 'cancelled' in b.status.lower()
    assert not b.busy and not b._cancel_requested
    assert target.read_bytes()==original


def test_cancel_during_stage3_facefusion_never_composites(tmp_path,monkeypatch):
    b=bridge(tmp_path)
    runtime=tmp_path/'facefusion-runtime'
    (runtime/'.venv/bin').mkdir(parents=True)
    for part in ['.venv/bin/python','facefusion.py','facefusion.ini']:
        (runtime/part).write_text('fixture')
    monkeypatch.setattr(integrations,'FACEFUSION_ROOT',runtime)
    b._stage_three_engine='facefusion_nsfw'
    b._active_stage_three_engine='facefusion_nsfw'
    b._set_busy(True)
    source=image(tmp_path/'source.png')
    target=image(tmp_path/'target.png')
    original=target.read_bytes()
    from genesis import person_a_targeting as pt
    def crops(target_file,source_file,regions,directory):
        t=image(Path(directory)/'crop-target.png')
        s=image(Path(directory)/'crop-source.png')
        return t,s
    monkeypatch.setattr(pt,'prepare_crops',crops)
    composite=Mock(side_effect=AssertionError('Cancelled stage 3 must not composite'))
    monkeypatch.setattr(pt,'composite_crop',composite)
    def simulated_run(command,**kwargs):
        b.cancelGeneration()
        image(Path(command[command.index('--output-path')+1]))
        return SimpleNamespace(returncode=0,stdout='late image saved')
    monkeypatch.setattr(b,'_run_local_facefusion_command',simulated_run)
    with use_route(Route('LOCAL','')):
        b._run_face_swap(target,source,(object(),object()))
    composite.assert_not_called()
    assert 'cancelled' in b.status.lower()
    assert not b.busy and not b._cancel_requested
    assert target.read_bytes()==original


def test_cancel_interrupts_real_child_promptly_without_touching_other_jobs(tmp_path,monkeypatch):
    b=bridge(tmp_path)
    b._set_busy(True)
    original_popen=subprocess.Popen
    created=[]
    ready=Event()
    def popen_capture(*args,**kwargs):
        child=original_popen(*args,**kwargs)
        created.append(child)
        ready.set()
        return child
    monkeypatch.setattr(c.subprocess,'Popen',popen_capture)
    result=[]
    def worker():
        try:
            b._run_local_facefusion_command([sys.executable,'-c','import time; time.sleep(30)'],cwd=tmp_path,timeout=35)
        except Exception as e:
            result.append(e)
    thread=Thread(target=worker,daemon=True)
    thread.start()
    assert ready.wait(timeout=5), 'Test child did not start'
    b.cancelGeneration()
    thread.join(timeout=5)
    if thread.is_alive():
        created[0].kill()
        thread.join(timeout=2)
        pytest.fail('Cancel did not interrupt its own process promptly')
    assert len(created)==1
    assert created[0].poll() is not None
    assert result and 'cancelled' in str(result[0]).lower()
    # Child was a temporary sleeping Python instance only; never FaceFusion.


def test_local_facefusion_timeout_reaps_only_its_own_child(tmp_path,monkeypatch):
    b=bridge(tmp_path)
    original_popen=subprocess.Popen
    created=[]
    def capture(*args,**kw):
        proc=original_popen(*args,**kw)
        created.append(proc)
        return proc
    monkeypatch.setattr(c.subprocess,'Popen',capture)
    with pytest.raises(subprocess.TimeoutExpired):
        b._run_local_facefusion_command([sys.executable,'-c','import time;time.sleep(30)'],cwd=tmp_path,timeout=0.15)
    assert len(created)==1 and created[0].poll() is not None


@pytest.mark.skipif(__import__('os').name != 'posix', reason='POSIX session/process-group behavior')
@pytest.mark.parametrize('stop_reason', ['timeout', 'cancel'])
def test_exited_wrapper_does_not_leave_its_descendant_running(tmp_path, monkeypatch, stop_reason):
    """A vanished launcher still has a live session when its child holds stdout.

    This regression exercises real harmless short-lived Python subprocesses.
    The test has its own unconditional group cleanup on failure.
    """
    import os
    import signal
    b = bridge(tmp_path)
    b._set_busy(True)
    child_pid_path = tmp_path / 'test-child.pid'
    child_code = ('import os,sys,time; from pathlib import Path; '
                  'Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(20)')
    wrapper_code = ('import subprocess,sys,time; '
                    f'subprocess.Popen([sys.executable,"-c",{child_code!r},{str(child_pid_path)!r}]);'
                    'time.sleep(.15)')
    original_popen = subprocess.Popen
    created = []
    def capture(*args, **kwargs):
        proc = original_popen(*args, **kwargs)
        created.append(proc)
        return proc
    monkeypatch.setattr(c.subprocess, 'Popen', capture)

    result = []
    finished = Event()
    def run():
        try:
            b._run_local_facefusion_command([sys.executable, '-c', wrapper_code],
                                            cwd=tmp_path, timeout=1.0)
        except Exception as exc:
            result.append(exc)
        finally:
            finished.set()
    thread = Thread(target=run, daemon=True)
    try:
        thread.start()
        started = time.monotonic()
        while time.monotonic()-started < 3 and not child_pid_path.exists():
            time.sleep(.01)
        assert child_pid_path.is_file(), 'Grandchild did not write its PID'
        child_pid = int(child_pid_path.read_text())
        while time.monotonic()-started < 3 and created and created[0].poll() is None:
            time.sleep(.01)
        assert created and created[0].poll() == 0, 'Wrapper must exit before cancellation'
        if stop_reason == 'cancel':
            b.cancelGeneration()
        assert finished.wait(timeout=4), 'Runner did not finish promptly'
        assert len(result) == 1
        if stop_reason == 'timeout':
            assert isinstance(result[0], subprocess.TimeoutExpired)
        else:
            assert 'cancelled' in str(result[0]).lower()
        # A killed child may be a short-lived zombie until the init process
        # reaps it; zombie != a runnable process still doing FaceFusion work.
        end=time.monotonic()+2
        def still_running(pid):
            try:
                stat=Path(f'/proc/{pid}/stat').read_text()
                return stat[stat.rfind(')')+2] not in ('Z', 'X')
            except (FileNotFoundError, ProcessLookupError):
                # Linux can remove a child's /proc entry between opening
                # and reading it; both errors mean it is no longer running.
                return False
        while time.monotonic() < end and still_running(child_pid):
            time.sleep(.02)
        assert not still_running(child_pid), 'Cancelled FaceFusion descendant survived its parent'
    finally:
        # Never let a broken test leave a synthetic sleeping descendant alive.
        if created and os.getpgrp() != created[0].pid:
            try:
                os.killpg(created[0].pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        thread.join(timeout=2)
