# PR #13 follow-up: live local ReActor GPU verification and UI artwork metadata review

Date: 15 October 2026. Tested on the user's Ubuntu host with AMD RX 9060 XT (16 GB VRAM) and local ComfyUI at `127.0.0.1:8188`. No RunPod connection, model downloads, service restarts, or changes to the user's active checkout.

## Live local ReActor verification (temporary, benign fixtures)

Two NASA photographs, catalogued as public domain on Wikimedia Commons, were downloaded to `/tmp/genesis-reactor-neutral-20261015` solely as **local test inputs**. They are **not included in the GitHub commit**, and the swapped portraits are not distributed. Image credit: NASA. No NASA endorsement is implied.

- Test source 1: https://commons.wikimedia.org/wiki/File:Astronaut_Joseph_Kerwin_portrait_(cropped2).jpg
- Test source 2: https://commons.wikimedia.org/wiki/File:Charles_Bolden_astronaut_photo.jpg

The PR's actual `GenerationBridge._run_face_swap` worker was executed three times, within an explicit `Route('LOCAL', '')` context and with confirmed `FaceRegion` pixel/digest bounds. Local `ReActorFaceSwapOpt`, `ReActorOptions`, `LoadImage`, and `SaveImage` nodes performed each real GPU job.

| Swap engine | Measured local elapsed time | Worker result | Compositing/preservation |
|---|---:|---|---|
| ReActor Inswapper (`inswapper_128.onnx`) | 9.2 sec | Completed | Within selected box changed, all pixels outside identical, originals identical |
| ReActor ReSwapper (`reswapper_256.onnx`) | 8.7 sec | Completed | Same checks passed |
| ReActor HyperSwap (`hyperswap_1a_256.onnx`) | 6.0 sec | Completed | Same checks passed |

**What these results establish:** the installed model weights and selected ReActor nodes can process benign two-portrait crops on the RX 9060 XT; the workflow composites the output to only the selected Person A box, leaves other pixels unchanged, and leaves source/target files unmodified. The backend queue returned to idle. These measurements are individual checks, **not stable speed benchmarks, identity similarity scores, NSFW capability certifications, or evidence of successful end-to-end GUI face selection**. Existing GUI/queue tests cover selection mechanics separately.

## Embedded generation metadata in UI graphics

Five existing PR graphics under `genesis/assets/home_buttons/` contained `tEXt` chunks with full ComfyUI `prompt` and `workflow` metadata (around 9–29 KB per image), including sampler seeds and installed model names. We detected no matching API credential, email address, or absolute home-path signatures using bounded metadata scans; this is not a guarantee no sensitive prompts are present. The five graphics were sanitized **without touching image data chunks**; a SHA-256 hash of RGBA pixels matched exactly for every file after stripping metadata. The original metadata-bearing versions were preserved, owner-only mode, in an external private review backup folder.

`tests/test_ui_artwork_privacy_20261015.py` prevents future accidental reintroduction of ComfyUI generation prompt/workflow/parameters metadata into UI assets.

**Important history limitation:** the original metadata-bearing images remain accessible through earlier commits of the public review branch until an approved, careful repository-history remediation is undertaken. This patch only cleans the current commit's published file contents. Do not force-push or rewrite protected/public history without explicit approval and a coordinated backup/release plan.

## Remaining before main integration

- Manual semantic review of the broader `main` reconciliation including pose/identity/model-family changes and nine UI artwork files.
- Confirm whether all nine artwork images can be redistributed publicly; image generation metadata by itself is not proof of ownership or commercial rights.
- Linux PR CI needs workflow authorization; Windows packaging CI must be rerun for this commit.
- Live RunPod 8189 model/pose/identity checks remain unverified while RunPod is unavailable. Local ReActor verification does not establish RunPod readiness.
