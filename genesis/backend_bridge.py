"""Qt controls for model-aware Local/RunPod routing, with read-only background discovery."""
import os
import threading
from pathlib import Path
from PyQt6.QtCore import QObject, QSettings, QTimer, pyqtProperty, pyqtSignal, pyqtSlot
from genesis.backend_routing import Route, choose_route, normalize_endpoint, use_route


_REMOTE_IDENTITY_MODELS = {
    "reactor_inswapper": "inswapper_128.onnx",
    "reactor_reswapper": "reswapper_256.onnx",
    "reactor_hyperswap": "hyperswap_1a_256.onnx",
}


def remote_identity_engines(info: dict) -> list[str]:
    """Return only identity engines advertised by the live ReActor node schema.

    Fail closed when ReActor is absent or its swap-model choices are not exposed.
    This keeps configured identity routes visible without claiming unavailable
    custom nodes or weights are usable on the current pod.
    """
    node = info.get("ReActorFaceSwap") or {}
    inputs = node.get("input") or {}
    values: set[str] = set()
    for group in ("required", "optional"):
        spec = (inputs.get(group) or {}).get("swap_model")
        if isinstance(spec, (list, tuple)) and spec and isinstance(spec[0], (list, tuple)):
            values.update(str(value) for value in spec[0] if value)
    available = {Path(value).name.casefold() for value in values}
    return [engine for engine, filename in _REMOTE_IDENTITY_MODELS.items()
            if filename.casefold() in available]


class BackendBridge(QObject):
    changed = pyqtSignal()
    profilesReady = pyqtSignal(object)
    statusReady = pyqtSignal(object)
    _received = pyqtSignal(object)

    def __init__(self, generation, parent=None):
        super().__init__(parent)
        self.generation = generation
        self.settings = QSettings('GENESIS', 'c0ckpit')
        requested = os.environ.get('GENESIS_BACKEND_MODE', '')
        legacy = os.environ.get('GENESIS_COMFY_URL', '')
        self._mode = requested or ('RUNPOD' if legacy else str(self.settings.value('backend/mode', 'AUTO')))
        if self._mode not in {'AUTO', 'LOCAL', 'RUNPOD'}:
            self._mode = 'AUTO'
        raw = os.environ.get('GENESIS_RUNPOD_URL', legacy or str(self.settings.value('backend/runpod_url', '')))
        self._message = 'Checking available backends…'
        try:
            self._endpoint = normalize_endpoint(raw)
        except ValueError as exc:
            self._endpoint = ''
            self._message = str(exc)
        self._local = []
        self._remote = []
        self._local_status = {'ready': False, 'comfyOnline': False, 'remote': False}
        self._remote_status = {'ready': False, 'comfyOnline': False, 'remote': True}
        self._running = False
        # RunPod is deliberately opt-in per app session. A saved endpoint is
        # configuration only; it must never cause background remote polling.
        self._connected = False
        self._local_safe = False
        self._revision = 0
        self._received.connect(self._accept)
        self.timer = QTimer(self)
        self.timer.setInterval(30000)
        self.timer.timeout.connect(self.refresh)
        generation.busyChanged.connect(self._publish)

    @pyqtProperty(str, notify=changed)
    def mode(self): return self._mode

    @pyqtProperty(str, notify=changed)
    def endpoint(self): return self._endpoint

    @pyqtProperty(str, notify=changed)
    def message(self): return self._message

    @pyqtProperty(bool, notify=changed)
    def checking(self): return self._running

    @pyqtProperty(bool, notify=changed)
    def connected(self): return self._connected

    @pyqtSlot(str)
    def setMode(self, mode):
        if self.generation.busy or mode not in {'AUTO', 'LOCAL', 'RUNPOD'}:
            return
        self._mode = mode
        self.settings.setValue('backend/mode', mode)
        self._publish()

    @pyqtSlot(str)
    def prepareModelRoute(self, model):
        """Use model-aware AUTO for an explicitly chosen model when needed.

        This never starts RunPod or changes a route during an active job.
        A selected verified local model can use AUTO when RunPod is offline.
        """
        if self.generation.busy or not model:
            return
        local_runnable = {p['model'] for p in self._local if p.get('runnable')}
        if model in local_runnable:
            # A deliberate selection of a verified local model may switch an
            # offline RUNPOD-only picker to AUTO. Running jobs never silently
            # fall back between backends.
            if (self._mode == 'RUNPOD' and not self._remote_status.get('ready')
                    and self._local_status.get('ready') and self._safe_local_model(model)):
                self._mode = 'AUTO'
                self.settings.setValue('backend/mode', 'AUTO')
                self._message = 'AUTO selected for installed local model · RunPod remains offline'
                self._publish()
                self.changed.emit()
            return
        import qt_cockpit as cockpit
        configured = {p['model'] for p in cockpit.configured_stage_one_profiles()}
        remote_known = {p['model'] for p in self._remote} | configured
        if model in remote_known and self._mode == 'LOCAL':
            self._mode = 'AUTO'
            self.settings.setValue('backend/mode', 'AUTO')
            self._message = 'AUTO selected for ' + model + ' · connect RunPod if the remote route is offline'
            self._publish()
            self.changed.emit()

    @pyqtSlot(str)
    def setEndpoint(self, value):
        if self.generation.busy:
            return
        try:
            endpoint = normalize_endpoint(value)
        except ValueError as exc:
            self._message = str(exc)
            self.changed.emit()
            return
        self._endpoint = endpoint
        self.settings.setValue('backend/runpod_url', endpoint)
        self._revision += 1
        self._remote = []
        self._remote_status = {'ready': False, 'comfyOnline': False, 'remote': True}
        self._publish()
        if self._connected:
            self.refresh()

    @pyqtSlot()
    def connectRemote(self):
        if self.generation.busy or self._connected:
            return
        if not self._endpoint:
            self._message = 'RunPod endpoint is not configured.'
            self.changed.emit()
            return
        self._connected = True
        self._revision += 1
        self._remote = []
        self._remote_status = {'ready': False, 'comfyOnline': False, 'remote': True}
        self._message = 'Connecting to RunPod…'
        self.timer.start()
        self.changed.emit()
        self.refresh()

    @pyqtSlot()
    def disconnectRemote(self):
        if not self._connected:
            return
        self._connected = False
        self.timer.stop()
        self._revision += 1
        self._remote = []
        self._remote_status = {'ready': False, 'comfyOnline': False, 'remote': True}
        self._message = 'RunPod disconnected · no background polling'
        self._publish()

    def start(self):
        # Probe local state once. RunPod remains untouched until Connect.
        self.refresh()

    @pyqtSlot()
    def refresh(self):
        if self._running:
            return
        self._running = True
        self.changed.emit()
        endpoint = self._endpoint if self._connected else ''
        threading.Thread(target=self._probe, args=(self._revision, endpoint), daemon=True).start()

    def _probe(self, revision, endpoint):
        import qt_cockpit as cockpit
        result = {'revision': revision}
        try:
            with use_route(Route('LOCAL', '')):
                result['local'] = cockpit.load_generation_profiles()
                result['local_status'] = cockpit.load_runtime_status()
                result['local_safe'] = bool(cockpit.integrations.gpu_kernel_preflight()[0])
        except Exception:
            result['local'] = []
            result['local_status'] = {'ready': False, 'comfyOnline': False, 'remote': False}
            result['local_safe'] = False
        result['remote'] = []
        result['remote_status'] = {'ready': False, 'comfyOnline': False, 'remote': True}
        if endpoint:
            try:
                with use_route(Route('RUNPOD', endpoint)):
                    result['remote_status'] = cockpit.load_runtime_status()
                    if result['remote_status'].get('ready'):
                        client = cockpit.workflow_lab.ComfyClient(endpoint, timeout=8)
                        info = cockpit.load_remote_catalog(client, refresh=True)
                        result['remote'] = cockpit.build_remote_generation_profiles(info)
                        engines = remote_identity_engines(info)
                        result['remote_status']['identityEngines'] = engines
                        result['remote_status']['identityReady'] = bool(engines)
            except Exception:
                result['remote_status']['ready'] = False
        self._received.emit(result)

    @pyqtSlot(object)
    def _accept(self, result):
        self._running = False
        if result['revision'] != self._revision:
            self.refresh()
            return
        self._local, self._remote = result['local'], result['remote']
        self._local_safe = result['local_safe']
        self._local_status, self._remote_status = result['local_status'], result['remote_status']
        self._publish()

    def resolve_operation(self, operation):
        """Capture an online destination; workers validate exact workflow assets.

        AUTO never starts services, and a failed operation never falls back to
        another backend. Explicit LOCAL is still subject to the kernel guard.
        """
        if operation not in {'face_swap', 'edit', 'inpaint', 'upscale'}:
            raise ValueError('Unsupported routed operation: ' + operation)
        if self._mode != 'RUNPOD' and self._local_safe and self._local_status.get('ready'):
            return Route('LOCAL', '')
        if self._mode != 'LOCAL' and self._connected and self._endpoint and self._remote_status.get('ready'):
            return Route('RUNPOD', self._endpoint)
        raise ValueError(f'{self._mode}: no ready safe backend for {operation}. Refresh backends in Create.')

    def _safe_local_model(self, model):
        import qt_cockpit as cockpit
        return self._local_safe and model in ({
            cockpit.FOUR_B_MODEL, cockpit.QWEN_MODEL,
            cockpit.REMOTE_PHR00T_V23_Q2_MODEL, cockpit.LOCAL_AISHA_9B_MODEL,
            cockpit.LOCAL_MIRACLEIN_9B_MODEL, cockpit.LOCAL_PORNMASTER_9B_MODEL,
        } | cockpit.REMOTE_SDXL_MODELS)

    def resolve(self, model):
        return choose_route(self._mode, model,
            {p['model'] for p in self._local if p.get('runnable')},
            {p['model'] for p in self._remote if p.get('runnable')},
            self._local_status.get('ready', False), self._remote_status.get('ready', False),
            self._endpoint, local_safe=BackendBridge._safe_local_model(self, model))

    @pyqtSlot()
    def _publish(self):
        if self.generation.busy:
            return
        # Always publish local and configured Stage-1 profiles for discovery;
        # the selected mode and route readiness govern execution separately.
        sources = ([row for row in self._local if row.get('ready')]
                   if self._mode == 'LOCAL' else self._local + self._remote)
        import qt_cockpit as cockpit
        configured_rows = {row['model']: row for row in cockpit.configured_stage_one_profiles()}
        merged_sources = []
        for source in list(sources):
            configured = configured_rows.get(source['model'])
            if configured:
                # Preserve configured stage roles even when the live/local row wins
                # readiness, paths and defaults for the same model.
                combined = dict(configured)
                combined.update(source)
                # A configured fallback row is remote-shaped. When a real local row
                # wins the merge it must keep its LOCAL origin, otherwise resolve()
                # can return LOCAL while the candidate still looks remote and the
                # publish step crashes trying to find a matching candidate.
                combined['remote'] = bool(source.get('remote', False))
                combined['stageOneConfigured'] = bool(configured.get('stageOneConfigured') or source.get('stageOneConfigured'))
                combined['stageOneEligible'] = bool(configured.get('stageOneEligible') or source.get('stageOneEligible'))
                combined['stageTwoConfigured'] = bool(configured.get('stageTwoConfigured') or source.get('stageTwoConfigured'))
                combined['stageTwoEligible'] = bool(configured.get('stageTwoEligible') or source.get('stageTwoEligible'))
                merged_sources.append(combined)
            else:
                merged_sources.append(source)
        present = {row['model'] for row in merged_sources}
        sources = merged_sources + [row for model, row in configured_rows.items() if model not in present]
        models = list(dict.fromkeys(row['model'] for row in sources))
        rows = []
        for model in models:
            candidates = [row for row in sources if row['model'] == model]
            try:
                route = self.resolve(model)
                source = next(row for row in candidates if bool(row.get('remote')) == (route.destination == 'RUNPOD'))
                row = dict(source, destination=route.destination, routeReady=True, selectable=True)
            except ValueError as exc:
                source = candidates[0]
                # Backend reachability and workflow executability are separate facts.
                # A model that is present in the live RunPod catalog still has a ready
                # route even when its current workflow validation blocks generation.
                route_ready = bool(
                    self._mode == 'RUNPOD' and self._connected and self._endpoint
                    and self._remote_status.get('ready') and source.get('remote')
                    and source.get('ready') and source.get('runnable')
                )
                installed = bool(source.get('ready'))
                if self._mode == 'LOCAL' and installed and not source.get('remote'):
                    destination = 'LOCAL INSTALLED · GPU BLOCKED'
                    note = 'Installed locally · workflow validated · execution disabled by the local GPU safety policy.'
                elif (self._mode == 'RUNPOD' and self._connected and self._remote_status.get('ready')
                      and source.get('remote') and not installed):
                    destination = 'UNAVAILABLE ON RUNPOD'
                    note = 'Configured · not present in the current RunPod ComfyUI catalog.'
                elif (self._mode == 'RUNPOD' and self._connected and self._remote_status.get('ready')
                      and source.get('remote') and installed):
                    destination = 'INSTALLED · WORKFLOW UNAVAILABLE'
                    note = source.get('note') or str(exc)
                else:
                    destination = ('INSTALLED · RUNPOD REQUIRED' if installed else
                                   ('RUNPOD OFFLINE' if source.get('remote') and self._endpoint else 'UNAVAILABLE'))
                    note = source.get('note') if not installed else str(exc)
                row = dict(source, runnable=False, routeReady=route_ready, selectable=False,
                           destination=destination, note=note)
            row['label'] = row['label'].removeprefix('RunPod · ')
            if not row['label'].endswith(' · ' + row['destination']):
                row['label'] += ' · ' + row['destination']
            rows.append(row)
        self.profilesReady.emit(rows)
        local = ('ready' if self._local_safe else 'safety blocked') if self._local_status.get('ready') else 'offline'
        remote = ('ready' if self._remote_status.get('ready') else 'offline') if self._connected else ('disconnected' if self._endpoint else 'not configured')
        self._message = f'Local {local} · RunPod {remote}'
        status = dict(self._remote_status if self._mode == 'RUNPOD' else self._local_status)
        status['routingSummary'] = self._message
        self.statusReady.emit(status)
        self.changed.emit()
