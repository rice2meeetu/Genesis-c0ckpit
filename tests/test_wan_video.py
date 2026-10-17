import pytest
from genesis.wan_video import build_prompt, availability, MODEL, ENCODER, VAE, NODES
from genesis.comfy_client import collect_outputs

def test_source_separate_and_native_settings():
    graph=build_prompt('untouched.png','Slow camera pan',frames=49,seed=123)
    assert graph['4']['inputs']['image']=='untouched.png'
    assert graph['8']['inputs']['start_image']==['4',0]
    assert graph['9']['inputs']['latent_image']==['8',0]
    assert graph['9']['inputs']['seed']==123
    assert graph['2']['inputs']['type']=='wan'
    assert graph['12']['inputs']['format']=='mp4'
    assert graph['5']['inputs']['text']=='Slow camera pan'

@pytest.mark.parametrize('args',[{'frames':50},{'frames':125},{'width':641},{'seed':-1}])
def test_invalid_controls_rejected(args):
    with pytest.raises(ValueError):build_prompt('source.png','Motion',**args)

def test_assets_and_nodes_gate_action():
    info={n:{} for n in NODES}
    for n,k,a in [('UNETLoader','unet_name',MODEL),('CLIPLoader','clip_name',ENCODER),('VAELoader','vae_name',VAE)]:
        info[n]={'input':{'required':{k:[[a]]}}}
    assert availability(info)['ready']
    del info['SaveVideo'];assert not availability(info)['ready']
    assert not availability({})['ready']

def test_video_outputs_collected():
    result=collect_outputs({'outputs':{'12':{'videos':[{'filename':'out.mp4','type':'output'}]}}})
    assert result[0]['kind']=='videos'
