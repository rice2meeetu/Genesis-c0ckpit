import argparse, copy, json, time, urllib.request
base='http://127.0.0.1:8188'
p=argparse.ArgumentParser()
p.add_argument('label')
args=p.parse_args()
def request(path, data=None):
    payload=None if data is None else json.dumps(data).encode()
    req=urllib.request.Request(base+path, data=payload, headers={'Content-Type':'application/json'})
    return json.load(urllib.request.urlopen(req,timeout=10))
queue=request('/queue')
if queue.get('queue_running') or queue.get('queue_pending'):
    raise SystemExit('REFUSING test: ComfyUI queue is not idle')
history=request('/history?max_items=50')
donor=None
for h in history.values():
    pp=h.get('prompt',[])
    if len(pp)<3: continue
    nn=pp[2]
    if len(nn)==7 and any('donutsdeliverymix' in str(n.get('inputs',{}).get('ckpt_name','')).lower() for n in nn.values()):
        donor=nn
        break
if not donor:
    donor={
      '1': {'class_type':'CheckpointLoaderSimple','inputs':{'ckpt_name':'donutsdeliverymixV4_v41.safetensors'}},
      '2': {'class_type':'CLIPTextEncode','inputs':{'clip':['1',1],'text':''}},
      '3': {'class_type':'CLIPTextEncode','inputs':{'clip':['1',1],'text':''}},
      '4': {'class_type':'EmptyLatentImage','inputs':{'width':512,'height':512,'batch_size':1}},
      '5': {'class_type':'KSampler','inputs':{'model':['1',0],'positive':['2',0],'negative':['3',0],'latent_image':['4',0],'seed':120001,'steps':8,'cfg':4.0,'sampler_name':'euler','scheduler':'normal','denoise':1.0}},
      '6': {'class_type':'VAEDecode','inputs':{'samples':['5',0],'vae':['1',2]}},
      '7': {'class_type':'SaveImage','inputs':{'images':['6',0],'filename_prefix':'GENESIS-speed-probe'}}
    }

results=[]
for iteration in range(3):
    nn=copy.deepcopy(donor)
    for node in nn.values():
        i=node.get('inputs',{})
        if node['class_type']=='CLIPTextEncode':
            i['text']='A simple red wooden cabin in a forest, realistic natural daylight'
        if node['class_type']=='KSampler':
            i.update(seed=120001+iteration, steps=8, cfg=4.0, sampler_name='euler', scheduler='normal', denoise=1.0)
        if node['class_type']=='EmptyLatentImage':
            i.update(width=512,height=512,batch_size=1)
        if node['class_type']=='SaveImage':
            node['class_type']='PreviewImage'
            node['inputs']={'images':i['images']}
    t=time.monotonic()
    receipt=request('/prompt',{'prompt':nn,'client_id':'genesis-speed-probe'})
    if 'error' in receipt: raise SystemExit(str(receipt))
    pid=receipt['prompt_id']
    for _ in range(480):
        time.sleep(.5)
        h=request('/history/'+pid)
        if pid in h:
            stat=h[pid]['status']
            if stat['status_str']!='success': raise RuntimeError(str(stat))
            break
    else: raise TimeoutError('Still running after 240 seconds')
    duration=round(time.monotonic()-t,3)
    results.append(duration)
    print(args.label,'trial',iteration+1,'sec',duration,flush=True)
print(json.dumps({'label':args.label,'seconds':results,'warm_avg_seconds':round(sum(results[1:])/2,3)}),flush=True)
