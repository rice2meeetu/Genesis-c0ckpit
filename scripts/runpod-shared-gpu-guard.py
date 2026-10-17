"""Coordinate ComfyUI instances sharing one GPU; never alter workflows or files.

A prompt holds a process-safe lock through execution and model cleanup. Failed
or killed processes automatically release the OS lock. Each service keeps its
own queue, history, output directory, and settings.
"""
import fcntl
import functools
import gc
import json
import logging
import os
from pathlib import Path
import time
import execution
import comfy.model_management as mm

LOCK = Path(os.environ.get('GENESIS_SHARED_GPU_LOCK', '/workspace/.genesis-shared-gpu.lock'))
EVENTS = Path(os.environ.get('GENESIS_SHARED_GPU_EVENTS', '/workspace/paul/shared-gpu-events.jsonl'))


def event(kind, prompt_id):
    data = {'event': kind, 'prompt_id': prompt_id, 'pid': os.getpid(), 'time': time.time()}
    try:
        with EVENTS.open('a') as f: f.write(json.dumps(data) + '\n')
    except OSError:
        logging.exception('[GENESIS shared GPU] Could not write diagnostic event')


def release_local_models(executor):
    mm.unload_all_models()
    # Drop this instance's model/tensor cache, keeping job results and history intact.
    executor.caches = execution.CacheSet(cache_type=executor.cache_type, cache_args=executor.cache_args)
    gc.collect()
    mm.soft_empty_cache()


def install_guard():
    original = execution.PromptExecutor.execute
    if getattr(original, '_genesis_shared_gpu_guard', False): return

    @functools.wraps(original)
    def guarded(self, prompt, prompt_id, extra_data=None, execute_outputs=None):
        extra_data = {} if extra_data is None else extra_data
        execute_outputs = [] if execute_outputs is None else execute_outputs
        mm.interrupt_current_processing(False)
        release_local_models(self)
        with LOCK.open('a+') as lock:
            waiting = False
            while True:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if not waiting:
                        logging.info('[GENESIS shared GPU] Job %s is waiting for the other instance', prompt_id)
                        event('waiting', prompt_id); waiting = True
                    if mm.processing_interrupted():
                        self.server.client_id = extra_data.get('client_id')
                        self.status_messages = []
                        self.success = False
                        self.history_result = {'outputs': {}, 'meta': {}}
                        self.add_message('execution_interrupted', {'prompt_id': prompt_id, 'node_id': None, 'node_type': None, 'executed': []}, broadcast=False)
                        event('cancelled_waiting', prompt_id)
                        return
                    time.sleep(0.2)
            event('acquired', prompt_id)
            logging.info('[GENESIS shared GPU] Job %s has the GPU', prompt_id)
            try:
                return original(self, prompt, prompt_id, extra_data, execute_outputs)
            finally:
                try:
                    release_local_models(self)
                except Exception:
                    logging.exception('[GENESIS shared GPU] Cleanup failed')
                finally:
                    event('released', prompt_id)
                    fcntl.flock(lock, fcntl.LOCK_UN)

    guarded._genesis_shared_gpu_guard = True
    execution.PromptExecutor.execute = guarded
    logging.info('[GENESIS shared GPU] Cross-instance prompt coordination enabled')


if os.environ.get("GENESIS_SHARED_GPU_SERIALIZE", "0") == "1":
    install_guard()
else:
    logging.info("[GENESIS shared GPU] Concurrent mode: serialization disabled")
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
