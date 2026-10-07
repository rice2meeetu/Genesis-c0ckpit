"""Native Wan 2.2 5B image-to-video; independent from still-image models."""
from pathlib import Path
from genesis.workflow_lab import _choice_values
MODEL = 'wan2.2_ti2v_5B_fp16.safetensors'
ENCODER = 'umt5_xxl_fp8_e4m3fn_scaled.safetensors'
VAE = 'wan2.2_vae.safetensors'
NODES = ('UNETLoader','CLIPLoader','VAELoader','LoadImage','CLIPTextEncode','ModelSamplingSD3','Wan22ImageToVideoLatent','KSampler','VAEDecode','CreateVideo','SaveVideo')
def availability(info):
    missing = [n for n in NODES if n not in info]
    for node, field, asset in [('UNETLoader','unet_name',MODEL),('CLIPLoader','clip_name',ENCODER),('VAELoader','vae_name',VAE)]:
        spec=info.get(node,{}).get('input',{}).get('required',{}).get(field)
        if asset not in _choice_values(spec): missing.append(asset)
    return {'ready':not missing,'reason':'Wan 2.2 5B ready.' if not missing else 'Missing: '+', '.join(missing)}
def build_prompt(image, prompt, width=640, height=384, frames=49, seed=0):
    if not image or not prompt.strip(): raise ValueError('Choose a source image and describe its motion.')
    if width%32 or height%32 or not 128<=width<=1280 or not 128<=height<=1280: raise ValueError('Video dimensions must be multiples of 32, from 128 to 1280.')
    if not 9<=frames<=121 or (frames-1)%4: raise ValueError('Use 9–121 frames in increments of four.')
    if not 0<=seed<2**63: raise ValueError('Invalid seed.')
    return {
        '1':{'class_type':'UNETLoader','inputs':{'unet_name':MODEL,'weight_dtype':'default'}},
        '2':{'class_type':'CLIPLoader','inputs':{'clip_name':ENCODER,'type':'wan','device':'default'}},
        '3':{'class_type':'VAELoader','inputs':{'vae_name':VAE}},
        '4':{'class_type':'LoadImage','inputs':{'image':image}},
        '5':{'class_type':'CLIPTextEncode','inputs':{'clip':['2',0],'text':prompt.strip()}},
        '6':{'class_type':'CLIPTextEncode','inputs':{'clip':['2',0],'text':'flicker, distorted geometry, blurry frames, abrupt motion'}},
        '7':{'class_type':'ModelSamplingSD3','inputs':{'model':['1',0],'shift':8.0}},
        '8':{'class_type':'Wan22ImageToVideoLatent','inputs':{'vae':['3',0],'start_image':['4',0],'width':width,'height':height,'length':frames,'batch_size':1}},
        '9':{'class_type':'KSampler','inputs':{'model':['7',0],'positive':['5',0],'negative':['6',0],'latent_image':['8',0],'seed':seed,'steps':20,'cfg':5.0,'sampler_name':'uni_pc','scheduler':'simple','denoise':1.0}},
        '10':{'class_type':'VAEDecode','inputs':{'samples':['9',0],'vae':['3',0]}},
        '11':{'class_type':'CreateVideo','inputs':{'images':['10',0],'fps':24.0}},
        '12':{'class_type':'SaveVideo','inputs':{'video':['11',0],'filename_prefix':'GENESIS-Wan','format':'mp4','codec':'auto'}}}
