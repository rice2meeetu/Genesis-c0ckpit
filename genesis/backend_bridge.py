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
        # A saved endpoint alone never causes polling. Connection requires
        # Connect or the explicit GENESIS_RUNPOD_AUTOCONNECT startup option.
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
        """Move explicit LOCAL selection back to model-aware AUTO when needed.

        This never starts or connects RunPod; it only prevents a RunPod-only
        Stage-1/2 choice from remaining trapped behind LOCAL routing.
        """
        if self.generation.busy or not model:
            return
        local_runnable = {p['model'] for p in self._local if p.get('runnable')}
        if model in local_runnable:
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
        requested = os.environ.get('GENESIS_RUNPOD_AUTOCONNECT', '').lower() in {'1', 'true', 'yes'}
        if requested and self._mode == 'RUNPOD' and self._endpoint:
            self.connectRemote()
        else:
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

    def resolve(self, model):
        import qt_cockpit as cockpit
        return choose_route(self._mode, model,
            {p['model'] for p in self._local if p.get('runnable')},
            {p['model'] for p in self._remote if p.get('runnable')},
            self._local_status.get('ready', False), self._remote_status.get('ready', False),
            self._endpoint, local_safe=model in {cockpit.FOUR_B_MODEL, cockpit.QWEN_MODEL, cockpit.REMOTE_PHR00T_V23_Q2_MODEL} and self._local_safe)

    @pyqtSlot()
    def _publish(self):
        if self.generation.busy:
            return
        # Match the published catalog to the selected routing mode.
        # LOCAL shows every installed/validated local profile, including profiles
        # intentionally execution-blocked by the local GPU safety policy. AUTO shows
        # both local and configured remote profiles. RUNPOD shows the remote catalog.
        sources = (
            [row for row in self._local if row.get('ready')] if self._mode == 'LOCAL'
            else self._remote if self._mode == 'RUNPOD'
            else self._local + self._remote
        )
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
        sources = merged_sources if self._mode == 'LOCAL' else (
            merged_sources + [row for model, row in configured_rows.items() if model not in present]
        )
        models = list(dict.fromkeys(row['model'] for row in sources))
        rows = []
        for model in models:
            candidates = [row for row in sources if row['model'] == model]
            try:
                route = self.resolve(model)
                source = next(row for row in candidates if bool(row.get('remote')) == (route.destination == 'RUNPOD'))
                row = dict(source, destination=route.destination, routeReady=True)
            except ValueError as exc:
                source = candidates[0]
                # Backend reachability and workflow executability are separate facts.
                # A model that is present in the live RunPod catalog still has a ready
                # route even when its current workflow validation blocks generation.
                route_ready = bool(
                    self._mode == 'RUNPOD' and self._connected and self._endpoint
                    and self._remote_status.get('ready') and source.get('remote')
                    and source.get('ready')
                )
                installed = bool(source.get('ready'))
                if self._mode == 'LOCAL' and installed and not source.get('remote'):
                    destination = 'LOCAL INSTALLED · GPU BLOCKED'
                    note = 'Installed locally · workflow validated · execution disabled by the local GPU safety policy.'
                else:
                    destination = ('RUNPOD' if route_ready else ('INSTALLED · RUNPOD REQUIRED' if installed else ('RUNPOD OFFLINE' if source.get('remote') and self._endpoint else 'UNAVAILABLE')))
                    note = source.get('note') if not installed else str(exc)
                row = dict(source, runnable=False, routeReady=route_ready,
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
