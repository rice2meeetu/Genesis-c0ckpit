from pathlib import Path
from unittest.mock import Mock
import os
import subprocess
import sys
import pytest
import qt_cockpit as cockpit
from genesis.backend_bridge import BackendBridge


def test_configured_stage_one_choices_never_claim_inactive_models_ready():
    rows = cockpit.configured_stage_one_profiles()
    assert {row['model'] for row in rows} == {
        cockpit.REMOTE_PHR00T_MODEL,
        cockpit.REMOTE_PHR00T_V23_GGUF_MODEL,
        cockpit.REMOTE_PHR00T_V23_Q2_MODEL,
        cockpit.REMOTE_PHR00T_V19_MODEL,
        cockpit.REMOTE_PHR00T_V19_GGUF_MODEL,
        cockpit.REMOTE_AISHA_9B_MODEL,
        cockpit.REMOTE_AISHA_BF16_MODEL,
        cockpit.REMOTE_MIRACLEIN_V2_MODEL,
        cockpit.REMOTE_MIRACLEIN_9B_MODEL,
        cockpit.REMOTE_PORNMASTER_9B_MODEL,
        cockpit.LOCAL_PORNMASTER_9B_MODEL,
        cockpit.REMOTE_DARKBEAST_9B_MODEL,
        cockpit.REMOTE_KLEIN_9B_MODEL,
        cockpit.FOUR_B_MODEL,
        cockpit.REGULAR_9B_MODEL,
        cockpit.KV_9B_MODEL,
        cockpit.QWEN_MODEL,
        cockpit.QWEN21_MODEL,
        cockpit.LOCAL_AISHA_9B_MODEL,
    }
    assert all(not row['runnable'] and not row['ready'] and row['stageOneConfigured'] for row in rows)


def test_runpod_selector_keeps_inactive_choices_but_refuses_generation():
    generation = cockpit.GenerationBridge()
    bridge = BackendBridge(generation)
    bridge._mode = 'RUNPOD'
    bridge._endpoint = 'https://test-8188.proxy.runpod.net'
    bridge._connected = True
    bridge._remote_status = {'ready': True}
    bridge._remote = cockpit.build_remote_generation_profiles({
        'UnetLoaderGGUF': {'input': {'required': {'unet_name': [[cockpit.REMOTE_PHR00T_MODEL]]}}}})
    published = []
    bridge.profilesReady.connect(published.append)
    bridge._publish()
    rows = {row['model']: row for row in published[-1]}
    assert rows[cockpit.REMOTE_PHR00T_MODEL]['routeReady']
    for model in [cockpit.REMOTE_PHR00T_V19_GGUF_MODEL, cockpit.REMOTE_AISHA_BF16_MODEL,
                  cockpit.REMOTE_MIRACLEIN_V2_MODEL]:
        assert not rows[model]['runnable']
        assert 'Not active' in rows[model]['note']
        with pytest.raises(ValueError, match='no ready backend'):
            bridge.resolve(model)
    assert {row['model'] for row in bridge._remote} == {cockpit.REMOTE_PHR00T_MODEL}


@pytest.mark.parametrize('model,workflow', [
    (cockpit.REMOTE_PHR00T_V19_GGUF_MODEL, cockpit.STAGE_1_WORKFLOW),
    (cockpit.REMOTE_PHR00T_V19_MODEL, cockpit.REMOTE_PHR00T_V19_WORKFLOW),
    (cockpit.REMOTE_AISHA_BF16_MODEL, cockpit.REMOTE_KLEIN9B_WORKFLOW),
    (cockpit.REMOTE_MIRACLEIN_V2_MODEL, cockpit.REMOTE_KLEIN9B_WORKFLOW),
])
def test_stage_one_choice_drives_workflow_and_passes_pose_and_result_forward(monkeypatch, tmp_path, model, workflow):
    monkeypatch.setenv('GENESIS_COMFY_URL', 'https://test-8188.proxy.runpod.net')
    bridge = cockpit.GenerationBridge()
    bridge._output_dir = tmp_path
    monkeypatch.setattr(bridge, '_connect_comfyui', lambda: (Mock(), {}))
    monkeypatch.setattr(cockpit, 'load_remote_catalog', lambda client: {})
    monkeypatch.setattr(cockpit, 'validate_remote_workflow_assets', Mock())
    stage1, stage2 = tmp_path / 'stage1.png', tmp_path / 'stage2.png'
    run = Mock(side_effect=[stage1, stage2])
    monkeypatch.setattr(bridge, '_run_reference_stage', run)
    source, pose = tmp_path / 'source.png', tmp_path / 'pose.png'
    bridge._run_generate('a ceramic mug', '', 512, 512, model,
                         'None', 'None', 'None', 0, 0, 0, source, pose,
                         True, False, False, {'stage2_model': cockpit.REMOTE_MIRACLEIN_V2_MODEL})
    first, second = run.call_args_list
    assert first.args[2:4] == (workflow, source)
    assert first.kwargs['model_override'] == model
    assert first.kwargs['secondary_image'] == pose
    assert second.args[3] == stage1
    assert second.kwargs['model_override'] == cockpit.REMOTE_MIRACLEIN_V2_MODEL


def test_stage_one_picker_and_card_share_selection_and_model_defaults(tmp_path):
    script = r'''
import sys, os, json
from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtQml import QQmlExpression
from PyQt6.QtWidgets import QApplication
import qt_cockpit_linux_premium as launcher
launcher.load_pose_items = lambda **kwargs: []
launcher.load_grok_preset_items = lambda: []
launcher.load_curated_pose_presets = lambda: []
launcher.load_runtime_status = lambda **kwargs: {}
launcher.BackendBridge.start = lambda self: None
engines = []
real_engine = launcher.QQmlApplicationEngine
def make_engine():
    engine = real_engine()
    engines.append(engine)
    return engine
launcher.QQmlApplicationEngine = make_engine

def verify():
    try:
        engine = engines[0]
        window = engine.rootObjects()[0]
        context = engine.rootContext()
        rows = [{'label':'Unmapped model', 'model':'unsupported', 'runnable':False, 'stageOneEligible':False},
                {'label':'Phr00t v23', 'model':'v23', 'loras':['None'], 'runnable':True,
                 'defaultSteps':4, 'defaultCfg':1.2},
                {'label':'Aisha', 'model':'aisha_nsfw_beta_v9_7_distilled_bf16.safetensors', 'stageTwoEligible':True, 'stageOneEligible':True, 'loras':['None'], 'runnable':False,
                 'defaultSteps':5, 'defaultCfg':1.0},
                {'label':'Miraclein', 'model':'miracleinNSFWGeneration_20FP8.safetensors', 'stageTwoEligible':True, 'stageOneEligible':True, 'loras':['None'], 'runnable':False,
                 'defaultSteps':12, 'defaultCfg':1.1}]
        window.setProperty('generationModel', rows)
        QApplication.processEvents()
        picker = window.findChild(QObject, 'stageOneModelPicker')
        assert picker is not None
        picker.setProperty('currentIndex', 2)
        expression = QQmlExpression(context, picker, 'activated(2)')
        expression.evaluate()
        assert not expression.hasError(), expression.error().toString()
        QApplication.processEvents()
        assert window.property('selectedModelName') == 'miracleinNSFWGeneration_20FP8.safetensors'
        assert window.property('generationSteps') == 12
        assert window.property('generationCfg') == 1.1
        repeater = window.findChild(QObject, 'generationStageRepeater')
        value, _ = QQmlExpression(context, repeater, 'itemAt(0)').evaluate()
        card = value.toQObject() if hasattr(value, 'toQObject') else value
        assert card.findChild(QObject, 'generationStageModel0').property('text') == 'Miraclein'
        # A catalog refresh must preserve an explicitly selected inactive choice.
        window.setProperty('generationModel', rows[::-1])
        QApplication.processEvents()
        assert window.property('selectedModelName') == 'miracleinNSFWGeneration_20FP8.safetensors'
        assert window.property('selectedGenerationIndex') == 0
        banner = window.findChild(QObject, 'mainPageBanner')
        assert banner is not None and not banner.property('visible')
        click = card.findChild(QObject, 'stageModelBoxClick0')
        expression = QQmlExpression(context, click, 'clicked(null)')
        expression.evaluate()
        assert not expression.hasError(), expression.error().toString()
        popup = window.findChild(QObject, 'stageModelPopup')
        assert popup.property('visible')
        QQmlExpression(context, window, 'selectStageChoice(0)').evaluate()
        for stage, choice, expected in [(1, 0, 'miracleinNSFWGeneration_20FP8.safetensors'),
                                         (2, 1, 'reactor_reswapper')]:
            value, _ = QQmlExpression(context, repeater, 'itemAt(' + str(stage) + ')').evaluate()
            stage_card = value.toQObject() if hasattr(value, 'toQObject') else value
            mouse = stage_card.findChild(QObject, 'stageModelBoxClick' + str(stage))
            expression = QQmlExpression(context, mouse, 'clicked(null)')
            expression.evaluate()
            assert not expression.hasError(), expression.error().toString()
            assert popup.property('visible')
            QQmlExpression(context, window, 'selectStageChoice(' + str(choice) + ')').evaluate()
            bridge = context.contextProperty('genesisBridge')
            if stage == 1:
                assert window.property('stageTwoModel') == expected
                assert bridge._stage_two_model == expected
                assert window.property('useStageTwo')
            else:
                assert window.property('stageThreeEngine') == expected
                assert bridge._stage_three_engine == expected
                assert window.property('useStageThree')
            assert not popup.property('visible')
        print("STAGE_ONE_SELECTION_OK")
        screenshot = os.environ.get('GENESIS_TEST_SCREENSHOT')
        if screenshot:
            window.showNormal()
            window.resize(1536, 960)
            def capture():
                expression = QQmlExpression(context, window.findChild(QObject, "genesisScene"),
                    'grabToImage(function(result) { result.saveToFile('
                    + json.dumps(screenshot) + '); Qt.quit(); })')
                expression.evaluate()
                assert not expression.hasError(), expression.error().toString()
            QTimer.singleShot(200, capture)
        else:
            QApplication.instance().exit(0)
    except Exception:
        import traceback
        traceback.print_exc()
        QApplication.instance().exit(1)
class CheckedApplication(QApplication):
    def exec(self):
        QTimer.singleShot(100, verify)
        QTimer.singleShot(10000, lambda: self.exit(2))
        return super().exec()
launcher.QApplication = CheckedApplication
sys.argv = ['stage-one-test', '--page', 'create']
sys.exit(launcher.main())
'''
    runtime = tmp_path / 'runtime'
    runtime.mkdir()
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', XDG_RUNTIME_DIR=str(runtime),
               QTWEBENGINE_DISABLE_SANDBOX='1', QT_QUICK_BACKEND='software',
               QSG_RHI_BACKEND='software', LIBGL_ALWAYS_SOFTWARE='1')
    result = subprocess.run([sys.executable, '-c', script], cwd=Path(__file__).resolve().parents[1],
                            env=env, text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "STAGE_ONE_SELECTION_OK" in result.stdout
