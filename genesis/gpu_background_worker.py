#!/usr/bin/env python3
import sys
from pathlib import Path
import onnxruntime as ort
from rembg import remove, new_session

providers = ort.get_available_providers()
preferred = [name for name in ("ROCMExecutionProvider", "CPUExecutionProvider") if name in providers]
if not preferred:
    raise SystemExit("No supported ONNX Runtime provider is available")

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
session = new_session("u2net", providers=preferred)
for raw in sys.argv[2:]:
    src = Path(raw)
    dst = out / (src.stem + "_cutout.png")
    dst.write_bytes(remove(src.read_bytes(), session=session))
    print("WROTE", dst, flush=True)
