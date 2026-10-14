"""Exercise Create's real QML handlers without services, jobs, or user settings."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


AUDIT_SCRIPT = r'''
import os, sys
from pathlib import Path
from PyQt6.QtCore import QObject, QTimer, QUrl, pyqtProperty, pyqtSlot
from PyQt6.QtQml import QQmlExpression
from PyQt6.QtWidgets import QApplication
import genesis.pose_workbench as handoff
handoff.POSE_WORKBENCH_HANDOFF_FILE = Path(os.environ['XDG_CONFIG_HOME'])/'isolated-handoff.json'
import qt_cockpit as c
import qt_cockpit_linux_premium as launch

scenario = sys.argv[1]
captures = []
route_calls = []
upscale_ready = scenario != 'unavailable-upscale'

class CaptureBridge(c.GenerationBridge):
    @pyqtProperty(bool, constant=True)
    def upscaleAvailable(self):
        return upscale_ready

    @pyqtSlot(str,str,int,int,str,str,str,str,str,bool,bool,bool,int,float,int,float,str,str,str,float,float,float)
    def queueGenerateAdvanced(self, *args):
        captures.append((tuple(args), self._output_target_long_edge))
        self._set_busy(True)

class CaptureBackend(launch.BackendBridge):
    def start(self):
        pass

    def resolve(self, model):
        # This fixture advertises a ready local model; pin that same route
        # for queue tests without requiring a live ComfyUI backend.
        return c.Route('LOCAL', '')

    def _publish(self):
        # Busy changes must not replace our deliberately isolated catalog.
        pass

    @pyqtSlot(str)
    def prepareModelRoute(self, model):
        route_calls.append(('model', model))

    @pyqtSlot(str)
    def setMode(self, mode):
        route_calls.append(('mode', mode))
        self._mode = mode
        self.changed.emit()

    @pyqtSlot(str)
    def setEndpoint(self, value):
        route_calls.append(('endpoint', value))
        self._endpoint = value
        self.changed.emit()

    @pyqtSlot()
    def connectRemote(self):
        route_calls.append(('connect',))
        self._connected = True
        self.changed.emit()

    @pyqtSlot()
    def disconnectRemote(self):
        route_calls.append(('disconnect',))
        self._connected = False
        self.changed.emit()

    @pyqtSlot()
    def refresh(self):
        route_calls.append(('refresh',))

launch.GenerationBridge = CaptureBridge
launch.BackendBridge = CaptureBackend
launch.load_pose_items = lambda **kwargs: []
launch.load_curated_pose_presets = lambda **kwargs: []
launch.load_grok_preset_items = lambda: []
launch.load_runtime_status = lambda **kwargs: {}
engines = []
real_engine = launch.QQmlApplicationEngine
launch.QQmlApplicationEngine = lambda: (engines.append(real_engine()) or engines[-1])

def verify():
    try:
        engine = engines[0]
        win = engine.rootObjects()[0]
        ctx = engine.rootContext()
        bridge = ctx.contextProperty('genesisBridge')
        def evaluate(code, scope=None):
            expression = QQmlExpression(ctx, scope or win, code)
            value, _ = expression.evaluate()
            assert not expression.hasError(), (code, expression.error().toString())
            QApplication.processEvents()
            return value

        def named(name):
            item = win.findChild(QObject, name)
            if item is None:
                item = evaluate("""(function() {
                    function find(item) {
                        if (item.objectName === NAME) return item;
                        if (item.children) for (var i=0; i<item.children.length; ++i) {
                            var found=find(item.children[i]);
                            if (found) return found;
                        }
                        return null;
                    }
                    return find(contentItem);
                })()""".replace('NAME',repr(name)))
            assert item is not None, name
            return item

        def text_button(text):
            items = [item for item in win.findChildren(QObject)
                     if item.property('text') == text and hasattr(item, 'clicked')]
            visible = [item for item in items if item.property('visible')]
            items = visible or items
            assert len(items) == 1, (text, len(items))
            return items[0]

        def click(item):
            assert item.property('enabled'), item.objectName() or item.property('text')
            evaluate('clicked()', item)

        model = c.REMOTE_DONUTS_MODEL
        row = dict(c.model_profile_settings(model, remote=False))
        row.update(model=model, label='Local Donuts', runnable=True, routeReady=True,
                   selectable=True, stageOneEligible=True, sourceSupported=True,
                   sourceRequired=False, poseReady=True, stageTwoEligible=False,
                   loras=['None'])
        win.setProperty('generationModel', [row])
        win.setProperty('generationPrompt', 'Neutral fully clothed portrait')
        QApplication.processEvents()
        assert named('generateButton').property('enabled')

        if scenario == 'unavailable-upscale':
            assert not bridge.upscaleAvailable
            assert not text_button('Final upscale').property('enabled')
            for name, target in [('quality2KButton', 2560), ('quality4KButton', 3840)]:
                assert not named(name).property('enabled'), name+' enabled without an installed upscale route'
                evaluate('applyOutputTarget('+str(target)+')')
                assert not win.property('useUpscale')
                assert win.property('generationOutputTarget') == 0
        elif scenario == 'unavailable-stage-two':
            # An installed stage-one model does not imply a refinement model exists.
            assert evaluate('stageTwoChoices.length') == 0
            assert named('generationPipelinePicker').property('count') == 1
            assert not text_button('Stage 2 · refine').property('enabled'), 'Stage 2 enabled without a selectable refinement model'
            win.setProperty('useStageTwo', True)
            QApplication.processEvents()
            assert not named('generateButton').property('enabled'), 'Generate enabled with an unavailable requested refinement stage'
            assert not named('enqueueGenerationButton').property('enabled')
        elif scenario == 'unavailable-stage-three':
            assert not win.property('stageThreeReady')
            assert not text_button('Stage 3 · review Person A face after generation').property('enabled')
            from PIL import Image
            source_file = Path(os.environ['XDG_CONFIG_HOME'])/'identity-source.png'
            Image.new('RGB', (64,64)).save(source_file)
            win.setProperty('generationSource', QUrl.fromLocalFile(str(source_file)))
            click(named('imageToImageModeButton'))
            assert named('generationPipelinePicker').property('count') == 1
            win.setProperty('useStageThree', True)
            QApplication.processEvents()
            assert not named('generateButton').property('enabled'), 'Generate enabled with an unavailable requested identity stage'
            assert not named('enqueueGenerationButton').property('enabled')
        elif scenario == 'stage-pipeline':
            from PIL import Image
            source_file = Path(os.environ['XDG_CONFIG_HOME'])/'identity-source.png'
            Image.new('RGB', (64,64)).save(source_file)
            win.setProperty('generationSource', QUrl.fromLocalFile(str(source_file)))
            click(named('imageToImageModeButton'))
            refinement = dict(c.model_profile_settings(c.REMOTE_AISHA_9B_MODEL, remote=True))
            refinement.update(model=c.REMOTE_AISHA_9B_MODEL, label='Aisha refinement',
                              stageTwoEligible=True, selectable=True, remote=True,
                              runnable=True, routeReady=True, loras=['None'])
            win.setProperty('generationModel', [row, refinement])
            ctx.setContextProperty('runtimeStatus', {'identityEngines':['reactor_reswapper']})
            QApplication.processEvents()
            assert not win.property('stageThreeReady'), 'Missing default engine must not count as ready'
            # Click the actual stage cards and the popup's concrete model choices.
            card = evaluate('itemAt(1)', named('generationStageRepeater'))
            assert card is not None
            evaluate('children[children.length - 1].clicked(null)', card)
            evaluate('itemAtIndex(0).clicked()', named('stageModelChoiceList'))
            assert win.property('stageTwoModel') == refinement['model']
            assert bridge._stage_two_model == refinement['model']
            assert win.property('stageTwoReady')
            card = evaluate('itemAt(2)', named('generationStageRepeater'))
            assert card is not None
            evaluate('children[children.length - 1].clicked(null)', card)
            evaluate('itemAtIndex(0).clicked()', named('stageModelChoiceList'))
            assert win.property('stageThreeEngine') == 'reactor_reswapper'
            assert bridge._stage_three_engine == 'reactor_reswapper'
            assert win.property('stageThreeReady')
            pipeline = named('generationPipelinePicker')
            assert pipeline.property('count') == 2
            pipeline.setProperty('currentIndex', 1)
            evaluate('activated(1)', pipeline)
            assert win.property('useStageTwo') and win.property('useStageThree')
            click(named('generateButton'))
            assert captures[-1][0][9:12] == (True, True, False)
            assert not pipeline.property('enabled')
            assert not named('stageOneModelPicker').property('enabled')
            assert not named('textToImageModeButton').property('enabled')
            assert not named('imageToImageModeButton').property('enabled')
            bridge._set_busy(False)
            QApplication.processEvents()
            pipeline.setProperty('currentIndex', 0)
            evaluate('activated(0)', pipeline)
            assert not win.property('useStageTwo') and not win.property('useStageThree')
        elif scenario == 'create-controls':
            from PIL import Image
            source_file = Path(os.environ['XDG_CONFIG_HOME'])/'source.png'
            pose_file = source_file.with_name('pose.png')
            Image.new('RGB', (64,64)).save(source_file)
            Image.new('RGB', (64,64)).save(pose_file)
            source = QUrl.fromLocalFile(str(source_file))
            pose = QUrl.fromLocalFile(str(pose_file))
            win.setProperty('generationSource', source)
            win.setProperty('selectedPoseSource', pose)
            for mode, source_arg, presets in [
                ('textToImageModeButton', '', row['createQualityPresets']),
                ('imageToImageModeButton', source.toString(), row['sourceQualityPresets'])
            ]:
                click(named(mode))
                for quality in ('Fast', 'Balanced', 'Quality'):
                    click(named('quality'+quality+'Button'))
                    assert win.property('generationWidth') == presets[quality]['width']
                    assert win.property('generationHeight') == presets[quality]['height']
                for name, target in [('quality2KButton',2560), ('quality4KButton',3840)]:
                    click(named(name))
                    assert win.property('generationOutputTarget') == target
                    assert win.property('useUpscale')
                click(named('qualityBalancedButton'))
                assert win.property('generationOutputTarget') == 0
                click(named('generateButton'))
                assert captures[-1][0][7:9] == (source_arg, pose.toString())
                assert not named('generateButton').property('enabled')
                assert named('enqueueGenerationButton').property('enabled')
                click(named('enqueueGenerationButton'))
                assert bridge.pendingGenerationCount == 1
                assert captures[-1][0][4] == model
                for _ in range(24):
                    click(named('enqueueGenerationButton'))
                assert bridge.pendingGenerationCount == 25
                assert not named('enqueueGenerationButton').property('enabled')
                # Repeater delegates have visual parents, so walk that tree.
                queue_controls = """(function() {
                    var found = [];
                    function visit(item) {
                        if (item.text === 'REMOVE' && typeof item.clicked === 'function') found.push(item);
                        if (item.children) for (var i=0; i<item.children.length; ++i) visit(item.children[i]);
                    }
                    visit(contentItem);
                    REPLACE_ACTION
                })()"""
                removal_count = evaluate(queue_controls.replace('REPLACE_ACTION','return found.length;'))
                assert removal_count == 25, ('visual queue remove controls', removal_count)
                evaluate(queue_controls.replace('REPLACE_ACTION','found[0].clicked();'))
                assert bridge.pendingGenerationCount == 24
                assert named('enqueueGenerationButton').property('enabled')
                click(named('clearWaitingQueueButton'))
                assert bridge.pendingGenerationCount == 0 and bridge.busy
                click(text_button('CANCEL'))
                assert bridge._cancel_requested
                bridge._set_busy(False)
                QApplication.processEvents()
                bridge._cancel_requested = False
            click(named('imageToImageModeButton'))
            win.setProperty('generationSource', QUrl())
            QApplication.processEvents()
            assert not named('generateButton').property('enabled')
            assert not named('enqueueGenerationButton').property('enabled')
            click(named('textToImageModeButton'))
            assert named('generateButton').property('enabled')
            # Explicit route controls call only their matching bridge operation.
            click(text_button('Save endpoint'))
            click(text_button('Connect RunPod'))
            click(text_button('Refresh'))
            click(text_button('Disconnect'))
            assert [call[0] for call in route_calls] == ['endpoint','connect','refresh','disconnect']
            # The real picker activation must choose the selected model's defaults.
            second = dict(c.model_profile_settings(c.REMOTE_MIRACLEIN_9B_MODEL, remote=True))
            second.update(model=c.REMOTE_MIRACLEIN_9B_MODEL, label='Miraclein', runnable=False,
                          routeReady=False, stageOneConfigured=True, remote=True, loras=['None'])
            win.setProperty('generationModel', [row, second])
            picker = named('stageOneModelPicker')
            picker.setProperty('currentIndex', 1)
            evaluate('activated(1)', picker)
            assert win.property('selectedModelName') == second['model']
            assert win.property('generationWidth') == second['createDefaults']['defaultWidth']
            assert not named('generateButton').property('enabled')
            assert route_calls[-1] == ('model', second['model'])
        else:
            raise AssertionError(scenario)
        print('BUTTON_AUDIT_OK', scenario, flush=True)
        QApplication.instance().exit(0)
    except Exception:
        import traceback
        traceback.print_exc()
        QApplication.instance().exit(1)

class CheckedApplication(QApplication):
    def exec(self):
        QTimer.singleShot(150, verify)
        QTimer.singleShot(15000, lambda: self.exit(2))
        return super().exec()

launch.QApplication = CheckedApplication
sys.argv = ['image-generation-button-audit', '--page', 'create']
sys.exit(launch.main())
'''


@pytest.mark.parametrize('scenario', [
    'create-controls', 'unavailable-upscale', 'unavailable-stage-two',
    'unavailable-stage-three', 'stage-pipeline',
])
def test_image_generation_buttons_in_actual_qml(tmp_path, scenario):
    runtime = tmp_path/'runtime'
    runtime.mkdir(mode=0o700)
    config = tmp_path/'config'
    config.mkdir()
    env = dict(os.environ,
        QT_QPA_PLATFORM='offscreen', QTWEBENGINE_DISABLE_SANDBOX='1',
        QT_QUICK_BACKEND='software', QSG_RHI_BACKEND='software',
        LIBGL_ALWAYS_SOFTWARE='1', GENESIS_RUNPOD_AUTOCONNECT='0',
        GENESIS_BACKEND_MODE='LOCAL', GENESIS_COMFY_URL='', GENESIS_RUNPOD_URL='',
        XDG_RUNTIME_DIR=str(runtime), XDG_CONFIG_HOME=str(config))
    result = subprocess.run([sys.executable, '-c', AUDIT_SCRIPT, scenario],
        cwd=Path(__file__).resolve().parents[1], env=env,
        capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout+'\n'+result.stderr
    assert 'BUTTON_AUDIT_OK '+scenario in result.stdout
