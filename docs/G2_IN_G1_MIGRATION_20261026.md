# GENESIS 2 → original GENESIS cockpit: integration ledger

This is an incremental and **non-destructive** integration of the two codebases.
Do not replace the original cockpit's generation pipeline with a bare G2 JSON file.
Do not upload model weights, personal image references, saved prompts or local pose
packs to this repository.

## Source precedence

1. Model author / exact-checkpoint ComfyUI API workflow (with documented revision).
2. Official ComfyUI family workflow.
3. Proven quantizer/community workflow for the same model, format and encoder.
4. A locally adapted workflow only with graph checks and a separately recorded
   successful GPU output. An accepted API prompt is not an image-quality result.

ComfyUI's regular frontend workflow (nodes/links) differs from API-format prompt
graphs (node IDs, class_type, inputs); do not substitute one format for the other.

## What the original cockpit already supplies

- Dark/gold Qt Quick UI, model selection and native ComfyUI API integration.
- A protected GPU/runtime routing policy and its own job queue and cancellation.
- Local-vs-remote RunPod routing, output/finishing stages and export handling.
- Curated skeleton browser, 70 textual pose descriptions, SDXL ControlNet routes,
  and several model-specific Qwen/Klein/PornMaster reference workflows.
- Family-specific model/LoRA compatibility and runtime quarantine. Keep those
  protections even if another project can parse an adapter's tensor keys.

## G2 features to reconcile, not blindly duplicate

| G2 candidate | Source evidence / status | G1 migration rule |
| --- | --- | --- |
| SDXL DonutsDeliveryMix | Model+CLIP LoRAs; OpenPoseXL2 skeleton conditioning in G2 | Compare G1's existing SDXL/pose route; preserve stronger working implementation |
| Aisha Klein 4B | Native four-step model; LoRA correctness not equivalent to GPU safety | Respect G1 4B adapter runtime hold |
| FLUX.2 Klein 9B-KV FP8 | Native FluxKVCache graph; 24 selectable experimental adapters | Do not copy G2's allowlist over G1's stricter KV quarantines |
| Lenovo UltraReal | PEFT loader and 140/140 shape checks | No G1 GPU enablement before live verified render |
| SNOFS 1.4 | Native LoKr loader and 112/112 shape checks | No G1 GPU enablement before live verified render |
| SmartphoneReality v13 | Conventional LoRA; native node/asset validation | Still needs controlled output checks |
| Phr00t v19 edit | Source image + optional second pose image | Compare original G1 Qwen and G2 graphs; keep source ordering |
| Phr00t v23 Q2 GGUF | Separate text encoder and VAE; Qwen's 16-channel latent; four-step author-style starting preset | Do not blindly replace G1's publisher-based defaults; inspect runtime graph, encoder and quantizer evidence |
| Krea Noct V4 | Independent Krea2 family, native graph; no G2 GPU render verified | Do not add to G1's working model picker without a native guarded route |
| Pose browser | 486 indexed skeleton PNGs; text Full-70 not 1:1 skeleton mapping | Reuse G1's curated pose index, enforce image existence and correct family route |
| Resolution/output | Native and final dimensions separate; exact output pixels via post-scale | Preserve G1's model-specific modes; do not claim post-scale = diffusion detail |
| Reliability | Targeted cancel, job UUID/recovery journal, no blind resubmission | Prefer/retain G1's existing queue policy; review G2-specific improvements individually |
| Performance | New end-to-end wall timing in successful G2 job metadata | Do not compare queue/download time to pure sampler time |

## First implemented bridge

- Adds an explicit "OPEN G2 STUDIO" button on the original cockpit's Linux
  Image Generation page.
- Checks for a complete local G2 install and starts its own virtualenv's
  Python interpreter with `main.py`, in the G2 directory.
- Does not modify G1's current model choice, queue, RunPod endpoint, service
  process, model weights, LoRA allowlists or existing QML routes.
- Does not download any weights or publish locally curated pose images.
- A second click while the window remains running does not start another G2
  process from the same cockpit session.

**This bridge is not a claim that the two backends are merged into one image
generator.** It provides safe access from G1 while staged in-process migration
is tested. The local G2 working tree may be ahead of the private GitHub
`Genesis-2/main` branch; inspect that working tree before copying files.

## Release gates

1. Run offline Python/QML smoke tests against the G1 integration branch.
2. Verify GUI button opens a single G2 window while preserving G1's queue.
3. Reconcile both versions of the workflow API graph for each model family.
4. Validate node registration and installed assets against the selected ComfyUI
   backend, not an unrelated RunPod or another user's machine.
5. Repeat safe GPU output checks only after relevant hardware warnings are
   addressed. Keep G1's runtime safety/quarantine holds intact.
6. Only after explicit visual acceptance should individual G2 capabilities be
   merged into G1's generation page, one family at a time.

## External reference

- ComfyUI API workflow format:
  https://docs.comfy.org/development/api-development/workflow-api-format
- ComfyUI official workflow examples:
  https://comfyanonymous.github.io/ComfyUI_examples/
