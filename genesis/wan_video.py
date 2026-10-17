"""Native WAN 2.2 5B and WAN 2.1 14B image-to-video workflows."""
from genesis.workflow_lab import _choice_values
MODEL = 'wan2.2_ti2v_5B_fp16.safetensors'
ENCODER = 'umt5_xxl_fp8_e4m3fn_scaled.safetensors'
VAE = 'wan2.2_vae.safetensors'
MODEL_14B = 'wan2.1_i2v_480p_14B_fp8_e4m3fn.safetensors'
VAE_14B = 'wan_2.1_vae.safetensors'
VISION_14B = 'clip_vision_h.safetensors'
LORA_14B = 'facefuck_epoch_80.safetensors'
NODES = ('UNETLoader','CLIPLoader','VAELoader','LoadImage','CLIPTextEncode','ModelSamplingSD3','Wan22ImageToVideoLatent','KSampler','VAEDecode','CreateVideo','SaveVideo')
NODES_14B = tuple(n for n in NODES if n != 'Wan22ImageToVideoLatent') + ('WanImageToVideo','CLIPVisionLoader','CLIPVisionEncode')

def availability(info, model=MODEL, lora=None):
    if model not in {MODEL, MODEL_14B}:
        return {'ready':False,'reason':'Choose a configured WAN model.'}
    if lora and (model != MODEL_14B or lora != LORA_14B):
        return {'ready':False,'reason':'This adapter is available only on the experimental 14B route.'}
    missing = [n for n in (NODES_14B if model==MODEL_14B else NODES) if n not in info]
    assets=[('UNETLoader','unet_name',model),('CLIPLoader','clip_name',ENCODER),('VAELoader','vae_name',VAE_14B if model==MODEL_14B else VAE)]
    if model==MODEL_14B:assets.append(('CLIPVisionLoader','clip_name',VISION_14B))
    if lora:
        if 'LoraLoaderModelOnly' not in info:missing.append('LoraLoaderModelOnly')
        assets.append(('LoraLoaderModelOnly','lora_name',lora))
    for node,field,asset in assets:
        spec=info.get(node,{}).get('input',{}).get('required',{}).get(field)
        if asset not in _choice_values(spec):missing.append(asset)
    label='WAN 2.1 14B' if model==MODEL_14B else 'WAN 2.2 5B'
    return {'ready':not missing,'reason':('Missing: '+', '.join(missing)) if missing else label+' ready.'+(' Adapter is experimental; its original training base is undocumented.' if lora else '')}

def build_prompt(image, prompt, width=640, height=384, frames=49, seed=0, *, model=MODEL, lora=None, lora_strength=0.5):
    if model not in {MODEL,MODEL_14B}:raise ValueError('Unknown WAN model.')
    if lora and (model != MODEL_14B or lora != LORA_14B):raise ValueError('Do not attach the 14B adapter to the 5B model.')
    if not 0<=lora_strength<=1:raise ValueError('Adapter strength must be between 0 and 1.')
    if not image or not prompt.strip():raise ValueError('Choose a source image and describe its motion.')
    if width%32 or height%32 or not 128<=width<=1280 or not 128<=height<=1280:raise ValueError('Video dimensions must be multiples of 32, from 128 to 1280.')
    if not 9<=frames<=121 or (frames-1)%4:raise ValueError('Use 9–121 frames in increments of four.')
    if not 0<=seed<2**63:raise ValueError('Invalid seed.')
    graph={
        '1':{'class_type':'UNETLoader','inputs':{'unet_name':model,'weight_dtype':'default'}},
        '2':{'class_type':'CLIPLoader','inputs':{'clip_name':ENCODER,'type':'wan','device':'default'}},
        '3':{'class_type':'VAELoader','inputs':{'vae_name':VAE_14B if model==MODEL_14B else VAE}},
        '4':{'class_type':'LoadImage','inputs':{'image':image}},
        '5':{'class_type':'CLIPTextEncode','inputs':{'clip':['2',0],'text':prompt.strip()}},
        '6':{'class_type':'CLIPTextEncode','inputs':{'clip':['2',0],'text':'flicker, distorted geometry, blurry frames, abrupt motion'}},
        '7':{'class_type':'ModelSamplingSD3','inputs':{'model':['1',0],'shift':8.0}},
        '8':{'class_type':'Wan22ImageToVideoLatent','inputs':{'vae':['3',0],'start_image':['4',0],'width':width,'height':height,'length':frames,'batch_size':1}},
        '9':{'class_type':'KSampler','inputs':{'model':['7',0],'positive':['5',0],'negative':['6',0],'latent_image':['8',0],'seed':seed,'steps':20,'cfg':5.0,'sampler_name':'uni_pc','scheduler':'simple','denoise':1.0}},
        '10':{'class_type':'VAEDecode','inputs':{'samples':['9',0],'vae':['3',0]}},
        '11':{'class_type':'CreateVideo','inputs':{'images':['10',0],'fps':24.0}},
        '12':{'class_type':'SaveVideo','inputs':{'video':['11',0],'filename_prefix':'GENESIS-Wan','format':'mp4','codec':'auto'}}}
    if model==MODEL_14B:
        graph['13']={'class_type':'CLIPVisionLoader','inputs':{'clip_name':VISION_14B}}
        graph['14']={'class_type':'CLIPVisionEncode','inputs':{'clip_vision':['13',0],'image':['4',0],'crop':'none'}}
        graph['8']={'class_type':'WanImageToVideo','inputs':{'positive':['5',0],'negative':['6',0],'vae':['3',0],'clip_vision_output':['14',0],'start_image':['4',0],'width':width,'height':height,'length':frames,'batch_size':1}}
        graph['9']['inputs'].update(positive=['8',0],negative=['8',1],latent_image=['8',2],cfg=6.0)
        graph['11']['inputs']['fps']=16.0
        graph['12']['inputs']['filename_prefix']='GENESIS-Wan14B'
    if lora:
        graph['15']={'class_type':'LoraLoaderModelOnly','inputs':{'model':['1',0],'lora_name':lora,'strength_model':lora_strength}}
        graph['7']['inputs']['model']=['15',0]
    return graph
