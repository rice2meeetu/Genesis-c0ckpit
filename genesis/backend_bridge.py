"""Qt controls for model-aware Local/RunPod routing, with read-only background discovery."""
import os
import threading
from PyQt6.QtCore import QObject, QSettings, QTimer, pyqtProperty, pyqtSignal, pyqtSlot
from genesis.backend_routing import Route, choose_route, normalize_endpoint, use_route


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

    @pyqtSlot(str)
    def setMode(self, mode):
        if self.generation.busy or mode not in {'AUTO', 'LOCAL', 'RUNPOD'}:
            return
        self._mode = mode
        self.settings.setValue('backend/mode', mode)
        self._publish()

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
        self.refresh()

    def start(self):
        self.timer.start()
        self.refresh()

    @pyqtSlot()
    def refresh(self):
        if self._running:
            return
        self._running = True
        self.changed.emit()
        threading.Thread(target=self._probe, args=(self._revision, self._endpoint), daemon=True).start()

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
        if self._mode != 'LOCAL' and self._endpoint and self._remote_status.get('ready'):
            return Route('RUNPOD', self._endpoint)
        raise ValueError(f'{self._mode}: no ready safe backend for {operation}. Refresh backends in Create.')

    def resolve(self, model):
        import qt_cockpit as cockpit
        return choose_route(self._mode, model,
            {p['model'] for p in self._local if p.get('runnable')},
            {p['model'] for p in self._remote if p.get('runnable')},
            self._local_status.get('ready', False), self._remote_status.get('ready', False),
            self._endpoint, local_safe=model == cockpit.FOUR_B_MODEL and self._local_safe)

    @pyqtSlot()
    def _publish(self):
        if self.generation.busy:
            return
        sources = (self._local if self._mode == 'LOCAL' else self._remote if self._mode == 'RUNPOD'
                   else self._local + self._remote)
        models = list(dict.fromkeys(row['model'] for row in sources))
        rows = []
        for model in models:
            candidates = [row for row in sources if row['model'] == model]
            try:
                route = self.resolve(model)
                source = next(row for row in candidates if bool(row.get('remote')) == (route.destination == 'RUNPOD'))
                row = dict(source, destination=route.destination, routeReady=True)
            except ValueError as exc:
                row = dict(candidates[0], runnable=False, routeReady=False, destination='UNAVAILABLE', note=str(exc))
            row['label'] = row['label'].removeprefix('RunPod · ')
            row['label'] += ' · ' + row['destination']
            rows.append(row)
        self.profilesReady.emit(rows)
        local = ('ready' if self._local_safe else 'safety blocked') if self._local_status.get('ready') else 'offline'
        remote = ('ready' if self._remote_status.get('ready') else 'offline') if self._endpoint else 'not configured'
        self._message = f'Local {local} · RunPod {remote}'
        status = dict(self._remote_status if self._mode == 'RUNPOD' else self._local_status)
        status['routingSummary'] = self._message
        self.statusReady.emit(status)
        self.changed.emit()
