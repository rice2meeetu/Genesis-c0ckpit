#!/usr/bin/env python3
import sys, json, contextlib
import cv2
import numpy as np
from insightface.app import FaceAnalysis
with contextlib.redirect_stdout(sys.stderr):
    app = FaceAnalysis(name="buffalo_l", root="/mnt/AI-Storage/ComfyUI/models/insightface", providers=["ROCMExecutionProvider", "CPUExecutionProvider"])
    app.prepare(ctx_id=0, det_size=(640, 640))
for line in sys.stdin:
    try:
        req = json.loads(line)
        image = cv2.imread(req["path"])
        if image is None:
            raise RuntimeError("OpenCV could not read image")
        with contextlib.redirect_stdout(sys.stderr):
            faces = app.get(image)
        result = []
        for face in faces:
            emb = np.asarray(face.embedding, dtype=np.float32)
            norm = float(np.linalg.norm(emb))
            if norm:
                emb = emb / norm
            x1, y1, x2, y2 = [int(round(float(v))) for v in face.bbox]
            result.append({"bbox":[x1,y1,x2,y2],"embedding":emb.tolist(),"det_score":float(face.det_score)})
        print(json.dumps({"ok":True,"faces":result}), flush=True)
    except Exception as exc:
        print(json.dumps({"ok":False,"error":str(exc)}), flush=True)
