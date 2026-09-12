#!/usr/bin/env python3
import sys
from pathlib import Path
import onnxruntime as ort
from rembg import remove, new_session
if "ROCMExecutionProvider" not in ort.get_available_providers():
    raise SystemExit("ROCMExecutionProvider unavailable")
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
session = new_session("u2net", providers=["ROCMExecutionProvider", "CPUExecutionProvider"])
for raw in sys.argv[2:]:
    src = Path(raw)
    dst = out / (src.stem + "_cutout.png")
    dst.write_bytes(remove(src.read_bytes(), session=session))
    print("WROTE", dst, flush=True)
