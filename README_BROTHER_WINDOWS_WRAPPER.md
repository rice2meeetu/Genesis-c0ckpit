# GENESIS — Brother Standalone Image Wrapper (Windows / Intel)

This is the brother-only Windows wrapper for the current GENESIS image-generation UI. It is separate from Paul's main Linux/RunPod GENESIS tree.

## What it does

- Runs the current graphite/gold GENESIS image-generation interface.
- Connects to an already-running ComfyUI backend.
- Supports AUTO, LOCAL, or remote routing from the Create page.
- Reads the live ComfyUI /object_info catalog, so model files do not need to live in Paul's Linux paths.
- Preserves the current Stage 1 / Stage 2 / Stage 3 controls and face-swap route supplied by the GENESIS workflows.
- Keeps model binaries out of this wrapper; ComfyUI owns and loads the models.

## Expected backend

Local ComfyUI normally uses http://127.0.0.1:8188.

Start ComfyUI first, then launch the wrapper. In AUTO, a ready local backend is used automatically. For a remote ComfyUI instance, enter its HTTPS endpoint in Create and choose the remote mode.

The wrapper itself does not run the diffusion models on the Intel CPU. It is the UI/client; inference happens in ComfyUI on whatever GPU/backend the brother already uses.

## Build once on the brother's Windows PC

1. Install Python 3.12 x64 if it is not already installed.
2. Extract this source package.
3. Double-click BUILD_BROTHER_WRAPPER_WINDOWS.bat.
4. When it reports BUILD PASS, use GENESIS-Brother-Image-Wrapper-Windows.zip.
5. Extract that ZIP anywhere and double-click RUN_BROTHER_WRAPPER.bat, or launch the EXE directly.

The build creates its own .venv-brother and does not modify another GENESIS installation.

## Model locations

Different Windows folders are fine. The wrapper discovers model names from the running ComfyUI catalog. If ComfyUI can see the model, the wrapper can see it.

Current GENESIS routes know these specialist names when present:

- Qwen-Rapid-NSFW-v23_Q8_0.gguf
- Qwen-Rapid-AIO-NSFW-v19.safetensors
- flux-2-klein-9b.safetensors
- aisha_nsfw_beta_v9_7_distilled_bf16.safetensors
- pornmasterFlux2Klein_v3-fp8.safetensors
- Miraclein NSFW v2.0 FP8 - Klein9B -,euler,cfg1.1.safetensors
- DarkBeast-Klein9b-V2-BFS-FP8-ComfyUI.safetensors

A file being visible does not by itself make a workflow runnable: required ComfyUI nodes, VAE/text encoders and workflow inputs are still validated before submission.

## Validation status

Validated on Paul's Linux machine without starting a GPU render:

- Python compilation: PASS
- Qt/QML Create-page software smoke: PASS
- GENESIS routing/generation unit tests: PASS
- Windows portability changes are isolated on branch brother-standalone-wrapper

Not yet validated because the brother's Windows machine is not connected here:

- Native Windows PyInstaller build
- His exact ComfyUI node catalog
- His exact model availability
- A live render on his backend

Run the Windows build, start his ComfyUI, then use Refresh in Create. The wrapper will report which backend and models are actually ready.
