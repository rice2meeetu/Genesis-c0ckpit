#!/usr/bin/env python3
"""Start only Paul's ComfyUI instance; keep the shared models and brother's port intact."""
import fcntl,os,subprocess,urllib.request
from pathlib import Path
base=Path('/workspace/paul')
with (base/'genesis-comfy-start.lock').open('w') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 try:
  urllib.request.urlopen('http://127.0.0.1:8189/system_stats',timeout=3).close()
  print('Paul ComfyUI is already running on 8189')
 except Exception:
  env=dict(os.environ,PYTHONPATH='/workspace/paul/genesis-python-deps', CUDA_MPS_PIPE_DIRECTORY='/tmp/genesis-mps-test', CUDA_MPS_LOG_DIRECTORY='/tmp/genesis-mps-test-log', CUDA_MPS_ACTIVE_THREAD_PERCENTAGE='50', GENESIS_SHARED_GPU_SERIALIZE='0')
  if not Path('/tmp/genesis-mps-test/nvidia-cuda-mps-control.pid').exists():
   subprocess.run(['nvidia-cuda-mps-control','-d'],env=env,check=True)
  root=base/'ComfyUI-genesis'
  args=[str(root/'.venv-cu128/bin/python'),'main.py','--listen','127.0.0.1','--port','8189','--user-directory',str(base/'user'),'--input-directory',str(base/'input'),'--output-directory',str(base/'output'),'--temp-directory',str(base/'temp'),'--database-url','sqlite:////workspace/paul/user/comfyui.db']
  p=subprocess.Popen(args,cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=(base/'comfy8189-genesis.log').open('a'),stderr=subprocess.STDOUT,start_new_session=True)
  (base/'genesis-comfy.pid').write_text(str(p.pid));print('Started Paul ComfyUI',p.pid)
