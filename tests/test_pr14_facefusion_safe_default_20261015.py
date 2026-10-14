"""FaceFusion provider defaults should reflect verified, not merely installed GPU support."""
from PyQt6.QtCore import QCoreApplication
import qt_cockpit as c


def test_cpu_is_initial_default_and_migraphx_remains_opt_in():
    QCoreApplication.instance() or QCoreApplication([])
    bridge = c.GenerationBridge()
    assert bridge.faceFusionProvider == 'cpu'
    bridge.setFaceFusionProvider('migraphx')
    assert bridge.faceFusionProvider == 'migraphx'
    bridge.setFaceFusionProvider('cpu')
    assert bridge.faceFusionProvider == 'cpu'


def test_provider_switch_disabled_during_busy_and_unknown_provider_denied():
    QCoreApplication.instance() or QCoreApplication([])
    bridge = c.GenerationBridge()
    bridge.setFaceFusionProvider('cuda')
    assert bridge.faceFusionProvider == 'cpu'
    bridge._set_busy(True)
    bridge.setFaceFusionProvider('migraphx')
    assert bridge.faceFusionProvider == 'cpu'
    bridge._set_busy(False)
    bridge.setFaceFusionProvider('migraphx')
    assert bridge.faceFusionProvider == 'migraphx'


def test_qml_distinguishes_experimental_gpu_from_default_cpu():
    qml=(c.PROJECT_ROOT/'genesis/qt_ui/MainPremiumLinux.qml').read_text()
    assert 'AMD GPU · MIGraphX (experimental)' in qml
    assert 'CPU · default' in qml
    assert 'currentIndex: genesisBridge.faceFusionProvider === "cpu" ? 1 : 0' in qml
