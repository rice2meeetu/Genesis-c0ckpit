"""Isolated CPU DWPose worker. Run only on explicit request from SkeletonEditor."""
from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
import sys


def extract(path: Path):
    # Set before importing torch/onnxruntime or the installed annotator.
    for key in ("HIP_VISIBLE_DEVICES","ROCR_VISIBLE_DEVICES","CUDA_VISIBLE_DEVICES"):
        os.environ[key]="-1"
    os.environ["AUX_ORT_PROVIDERS"]="CPUExecutionProvider"
    os.environ["OMP_NUM_THREADS"]="2"
    os.environ["OPENBLAS_NUM_THREADS"]="2"

    root=Path.home()/"AI"/"ComfyUI"/"custom_nodes"/"comfyui_controlnet_aux"
    weights=root/"ckpts"/"yzd-v"/"DWPose"
    det=weights/"yolox_l.onnx"
    pose=weights/"dw-ll_ucoco_384.onnx"
    if not all(p.is_file() and p.stat().st_size>100_000_000 for p in (det,pose)):
        raise RuntimeError("Local DWPose detector weights are missing or incomplete.")
    if not path.is_file():
        raise ValueError("Reference image is unavailable.")
    if path.stat().st_size>40*1024*1024:
        raise ValueError("Reference image exceeds 40 MB.")
    from PIL import Image,ImageOps
    with Image.open(path) as opened:
        if opened.width*opened.height>32_000_000:
            raise ValueError("Reference image exceeds 32 megapixels.")
        image=ImageOps.exif_transpose(opened).convert("RGB")
        image.thumbnail((1024,1024),Image.Resampling.LANCZOS)
        import numpy as np
        pixels=np.asarray(image)
    sys.path.insert(0,str(root/"src"))
    # Wholebody receives local absolute paths directly, so this never calls
    # the annotator's download helper. Restrict ONNX Runtime to CPU explicitly.
    with contextlib.redirect_stdout(sys.stderr):
        import onnxruntime as ort
        from custom_controlnet_aux.dwpose.wholebody import Wholebody
        from custom_controlnet_aux.dwpose import DwposeDetector
        from custom_controlnet_aux.dwpose.util import guess_onnx_input_shape_dtype
        options=ort.SessionOptions()
        options.intra_op_num_threads=2
        whole=Wholebody(None,None,torchscript_device="cpu")
        whole.det=ort.InferenceSession(str(det),sess_options=options,providers=["CPUExecutionProvider"])
        whole.pose=ort.InferenceSession(str(pose),sess_options=options,providers=["CPUExecutionProvider"])
        whole.det_filename=det.name
        whole.pose_filename=pose.name
        whole.pose_input_size,_=guess_onnx_input_shape_dtype(pose.name)
        assert whole.det.get_providers()==["CPUExecutionProvider"]
        assert whole.pose.get_providers()==["CPUExecutionProvider"]
        detector=DwposeDetector(whole)
        _,data=detector(pixels,include_body=True,include_hand=True,
                        include_face=True,image_and_json=True)
    from genesis.pose_document import validate_document
    document=validate_document(data)
    if not document["people"]:
        raise ValueError("DWPose found no people. Try a clearer photo or import pose JSON.")
    return document


def main():
    if len(sys.argv)!=2:
        raise SystemExit("Usage: pose_extract_cpu IMAGE")
    try:
        print(json.dumps(extract(Path(sys.argv[1]))),flush=True)
    except Exception as exc:
        print(str(exc),file=sys.stderr,flush=True)
        raise SystemExit(1)


if __name__=="__main__":
    main()
