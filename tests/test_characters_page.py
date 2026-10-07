from pathlib import Path
from unittest.mock import Mock
import pytest
import qt_cockpit as c
from genesis.backend_routing import Route, use_route
from genesis.character_library import save_character, add_reference, set_reference_details, preferred_reference, update_reference, character_items


def test_candidates_approval_and_replacement_preserve_master(tmp_path):
    master = tmp_path / 'master.png'; master.write_bytes(b'master')
    candidate = tmp_path / 'candidate.png'; candidate.write_bytes(b'candidate')
    replacement = tmp_path / 'replacement.png'; replacement.write_bytes(b'replacement')
    index = tmp_path / 'characters.json'
    row = save_character('Character A', str(master), adult_confirmed=True, path=index)
    add_reference(row['id'], str(candidate), role='Profile', path=index)
    set_reference_details(row['id'], str(candidate), 'face', False, path=index)
    assert preferred_reference(row['id'], 'Profile', index) == str(master)
    set_reference_details(row['id'], str(candidate), 'face', True, path=index)
    assert preferred_reference(row['id'], 'Profile', index) == str(candidate)
    set_reference_details(row['id'], str(candidate), 'ignore', True, path=index)
    assert preferred_reference(row['id'], 'Profile', index) == str(master)
    update_reference(row['id'], str(candidate), str(replacement), path=index)
    assert character_items(index)[0]['referenceItems'][1]['category'] == 'ignore'
    with pytest.raises(ValueError, match='Master identity'):
        set_reference_details(row['id'], str(master), 'pose', False, path=index)
    assert master.read_bytes() == b'master'


@pytest.mark.parametrize('model', [c.REMOTE_DONUTS_MODEL, c.REMOTE_BIGLUSTY_DONUT_MODEL])
def test_sdxl_source_route_encodes_source_and_honors_controls(monkeypatch, tmp_path, model):
    bridge = c.GenerationBridge()
    client = Mock(); client.upload_image.return_value = {'name': 'source.png', 'subfolder': 'uploads'}
    monkeypatch.setattr(bridge, '_connect_comfyui', lambda: (client, {}))
    graph = {'1': {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': model}},
             '3': {'class_type': 'CLIPTextEncode', 'inputs': {}},
             '5': {'class_type': 'KSampler', 'inputs': {'latent_image': ['4', 0], 'denoise': 1., 'steps': 25, 'cfg': 4., 'seed': 0, 'sampler_name': 'euler', 'scheduler': 'karras'}}}
    monkeypatch.setattr(c, 'build_create_prompt', lambda *args: graph)
    monkeypatch.setattr(c, 'validate_operation_prompt', Mock())
    submit = Mock(return_value=tmp_path/'result.png'); monkeypatch.setattr(bridge, '_submit_and_save', submit)
    bridge._output_dir = tmp_path
    source = tmp_path/'source.png'; source.write_bytes(b'source')
    with use_route(Route('LOCAL', '')):
        bridge._run_generate('portrait', '', 1024, 1024, model, 'None', 'None', 'None', 0, 0, 0, source, None, False, False, False,
                             {'denoise': .35, 'seed': 123})
    submit.assert_called_once()
    client.upload_image.assert_called_once_with(source)
    assert graph['5']['inputs']['latent_image'] == ['genesis_source_encode', 0]
    assert graph['genesis_source_encode']['inputs']['vae'] == ['1', 2]
    assert graph['5']['inputs']['denoise'] == .35
    assert graph['5']['inputs']['seed'] == 123
    assert bridge._original_master == source

@pytest.mark.parametrize('model', [c.REMOTE_DONUTS_MODEL, c.REMOTE_BIGLUSTY_DONUT_MODEL])
def test_sdxl_pose_controls_conditioning_without_replacing_source_latent(model):
    graph = {'5': {'inputs': {'latent_image': ['genesis_source_encode', 0]}}, '1': {'inputs': {'ckpt_name': model}}}
    info = {'ControlNetLoader': {'input': {'required': {'control_net_name': [[c.REMOTE_SDXL_POSE_CONTROLNET]]}}}}
    c.attach_sdxl_pose(graph, info, {'name': 'pose.png'}, 1024, 1024)
    assert graph['5']['inputs']['latent_image'] == ['genesis_source_encode', 0]
    assert graph['5']['inputs']['positive'] == ['genesis_pose_apply', 0]
    assert graph['genesis_pose_controlnet']['inputs']['control_net_name'] == 'OpenPoseXL2.safetensors'


def test_generate_uses_typed_prompt_or_pose_prompt():
    import re
    from PyQt6.QtQml import QJSEngine
    qml = (c.UI_ROOT/'MainPremiumLinux.qml').read_text()
    fn = re.search(r'    function generateCurrent\(\).*?\n    }', qml, re.S).group()
    engine = QJSEngine()
    engine.evaluate('var captured; var genesisBridge={queueGenerateAdvanced:function(p){captured=p}}; var generationPrompt="", selectedPosePrompt="pose description", generationNegativePrompt="", generationWidth=1024,generationHeight=1024,selectedGenerationProfile={model:"sdxl"},selectedLora="None",selectedLoraTwo="None",generationSource="source",selectedPoseSource="pose",useStageTwo=false,useStageThree=false,useUpscale=false,generationSteps=25,generationCfg=4,generationSeed=1,generationDenoise=.65,generationSampler="euler",generationScheduler="karras",selectedLoraThree="None",selectedLoraStrength=0,selectedLoraTwoStrength=0,selectedLoraThreeStrength=0;')
    assert not engine.evaluate(fn).isError()
    engine.evaluate('generateCurrent()')
    assert engine.evaluate('captured').toString() == 'pose description'
    engine.evaluate('generationPrompt="custom instruction"; generateCurrent()')
    assert engine.evaluate('captured').toString() == 'custom instruction'


def test_best_reference_only_uses_approved_identity_angles(tmp_path):
    from genesis.character_library import best_reference
    index=tmp_path/'library.json'
    master=tmp_path/'master';master.write_bytes(b'm')
    left=tmp_path/'left';left.write_bytes(b'l')
    row=save_character('A',str(master),adult_confirmed=True,path=index)
    add_reference(row['id'],str(left),role='¾ Left',category='face',approved=False,path=index)
    assert best_reference(row['id'],'three-quarter left portrait',index)==str(master)
    set_reference_details(row['id'],str(left),'face',True,path=index)
    assert best_reference(row['id'],'three-quarter left portrait',index)==str(left)
    set_reference_details(row['id'],str(left),'pose',True,path=index)
    assert best_reference(row['id'],'three-quarter left portrait',index)==str(master)


def test_reference_batch_keeps_master_and_stores_unapproved_candidates(monkeypatch,tmp_path):
    from genesis.character_library import load_characters, REFERENCE_BUILD_REQUESTS
    index=tmp_path/'library.json';master=tmp_path/'master';master.write_bytes(b'm')
    row=save_character('A',str(master),adult_confirmed=True,path=index)
    real_add=c.add_reference
    monkeypatch.setattr(c,'add_reference',lambda cid,image,**kw:real_add(cid,image,path=index,**kw))
    import genesis.character_library as library
    real_sheet=library.save_reference_sheet
    monkeypatch.setattr(library,'save_reference_sheet',lambda cid,image:real_sheet(cid,image,path=index))
    b=c.GenerationBridge();b._output_dir=tmp_path;b._set_busy(True)
    calls=[]
    def generate(*args,**kwargs):
        assert b.busy and kwargs['release_busy'] is False
        assert args[11]==master
        path=tmp_path/f'candidate-{len(calls)}.png'
        from PIL import Image
        Image.new('RGB',(16,16),'grey').save(path)
        calls.append(path);return path
    monkeypatch.setattr(b,'_run_generate',generate)
    b._run_character_reference_set(Route('LOCAL',''),row['id'],master,c.REMOTE_DONUTS_MODEL)
    saved=load_characters(index)[0]
    assert saved['primary_image']==str(master) and len(calls)==len(REFERENCE_BUILD_REQUESTS)
    assert all(saved['reference_approved'][str(p)] is False for p in calls)
    assert not b.busy and master.read_bytes()==b'm'


def test_facefusion_runner_uses_existing_runtime_without_undefined_state(monkeypatch,tmp_path):
    b=c.GenerationBridge();b._output_dir=tmp_path;b._facefusion_provider='cpu'
    target=tmp_path/'target.png';target.write_bytes(b't');source=tmp_path/'source.png';source.write_bytes(b's')
    def run(command,**kwargs):
        Path(command[command.index('--output-path')+1]).write_bytes(b'out')
        assert '--workflow-mode' in command
        return Mock(returncode=0,stdout='done')
    monkeypatch.setattr(c.subprocess,'run',run)
    b._run_facefusion(target,source,Path('/runtime/python'),Path('/runtime/facefusion.py'),Path('/runtime/facefusion.ini'))
    assert b.status.startswith('FaceFusion complete')


def test_reference_batch_stops_on_failure_and_keeps_earlier_candidates(monkeypatch,tmp_path):
    from genesis.character_library import load_characters
    index=tmp_path/'library.json';master=tmp_path/'master';master.write_bytes(b'm')
    row=save_character('A',str(master),adult_confirmed=True,path=index)
    real_add=c.add_reference
    monkeypatch.setattr(c,'add_reference',lambda cid,image,**kw:real_add(cid,image,path=index,**kw))
    candidate=tmp_path/'candidate';candidate.write_bytes(b'c')
    b=c.GenerationBridge();b._set_busy(True)
    generation=Mock(side_effect=[candidate,None]);monkeypatch.setattr(b,'_run_generate',generation)
    b._run_character_reference_set(Route('LOCAL',''),row['id'],master,c.REMOTE_DONUTS_MODEL)
    assert generation.call_count==2 and not b.busy
    saved=load_characters(index)[0]
    assert saved['references']==[str(master),str(candidate)]
    assert saved['reference_approved'][str(candidate)] is False


def test_local_face_finishing_respects_selected_swap_engine(monkeypatch,tmp_path):
    import copy
    from genesis.comfy_client import ComfyClient
    graph={'1':{'class_type':'LoadImage','inputs':{'image':'target'}},'2':{'class_type':'LoadImage','inputs':{'image':'source'}},'3':{'class_type':'ReActorFaceSwap','inputs':{'swap_model':'inswapper_128.onnx','face_restore_model':'none','codeformer_weight':0}}}
    monkeypatch.setattr(c.workflow_lab,'workflow_to_prompt',lambda *a:copy.deepcopy(graph))
    monkeypatch.setattr(c.workflow_lab,'discover_workflow_controls',lambda p:{'images':[('1','image'),('2','image')]})
    monkeypatch.setattr(c.workflow_lab,'validate_prompt',lambda *a:{'valid':True,'missing_nodes':[],'missing_inputs':[]})
    b=c.GenerationBridge();b._stage_three_engine='reactor_hyperswap'
    client=Mock();client.upload_image.return_value={'name':'image.png'}
    submit=Mock(return_value=tmp_path/'output');monkeypatch.setattr(b,'_submit_and_save',submit)
    with use_route(Route('LOCAL','')):
        b._run_reference_stage(client,{},c.STAGE_3_WORKFLOW,tmp_path/'target','', 'stamp','FaceLock',secondary_image=tmp_path/'source')
    actual=submit.call_args.args[1]
    assert actual['3']['inputs']['swap_model']=='hyperswap_1a_256.onnx'


def test_facefusion_gpu_failure_does_not_launch_cpu_fallback(monkeypatch,tmp_path):
    b=c.GenerationBridge();b._output_dir=tmp_path
    run=Mock(return_value=Mock(returncode=1,stdout='AMD GPU is not accessible to this process'))
    monkeypatch.setattr(c.subprocess,'run',run)
    b._run_facefusion(tmp_path/'target',tmp_path/'source',Path('/runtime/python'),Path('/runtime/facefusion.py'),Path('/runtime/config.ini'))
    run.assert_called_once()
    assert 'AMD GPU is not accessible' in b.status and not b.busy
    assert not list(tmp_path.glob('GENESIS-FaceFusion-*'))
