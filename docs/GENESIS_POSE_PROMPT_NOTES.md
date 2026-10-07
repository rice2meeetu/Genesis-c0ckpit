# GENESIS pose, identity and prompt research

Reviewed public model-author documentation, Hugging Face discussions, GitHub and Reddit text discussions on 7 October 2026. Civitai searches returned no usable indexed material and direct pages/API requests failed; private Discord/community groups were not accessible. No imagery was generated or inspected.

## Findings applied

- [RefControl author documentation](https://github.com/thedeoxen/refcontrol): ordered pose/control first, identity reference second; exact trigger `apply pose from image 1 with reference from image 2`; suggested adapter strength 0.8–1.0. GENESIS defaults to 0.9 and retains manual control. Use an appropriate skeleton/control representation and matching framing/proportions. Its 9B pose adapter is not interchangeable with the author's 4B depth adapter.
- [Phr00t model card](https://huggingface.co/Phr00t/Qwen-Image-Edit-Rapid-AIO): v19 favors edit consistency; v23 favors instruction adherence. The author recommends 4–8 steps with beta scheduling; v19 supports er_sde or euler_ancestral, v23 recommends euler_ancestral. GENESIS retains existing CFG choices, and fixes v23 Q2 to use the same v23 defaults as its sibling routes. It uses a separate edit instruction rather than Klein's adapter trigger. Explicitly assigning identity to image1 and pose/composition to image2 supports the intended edit, but is not an identity guarantee.
- [Official Klein Base 9B card](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B): Base is undistilled; its published example uses 50 steps and guidance 4. GENESIS now separates that base checkpoint's defaults from the four-step distilled route. These are author starting settings, not proof of optimum output on every reference.
- Shared I2I prompt requirements: natural realistic skin texture, coherent anatomy, natural proportions, fine hair/detail, photographic lighting and sharpness. Identity wording preserves recognizable features while allowing pose, viewpoint, expression and lighting to change. Refinement inherits the realism instruction instead of repeating it. No extra appearance LoRAs are silently added. SDXL retains its own positive/negative conditioning.

## Community context and limits

[Reddit pose-transfer discussion](https://www.reddit.com/r/StableDiffusion/comments/1np8lfv/qwenimageedit2509_pose_transfer_no_lora_required/) describes using a skeleton as a separate Qwen reference. [Another multi-reference discussion](https://www.reddit.com/r/StableDiffusion/comments/1q3704y/qwen_image_edit_references/) reports identity/control blending despite numbered prompts. These are anecdotes, not verified defaults. They reinforce testing the graph's separate inputs rather than promising that wording alone locks identity. Production configuration decisions above use author sources.

Denoise advice is graph-specific: lower denoise can retain source detail in SDXL's source-encoded latent but restrict a pose change. Phr00t's empty-latent editing graph does not gain that same guarantee by lowering denoise. Steps, CFG and a fixed seed do not independently guarantee facial identity. GENESIS displays this guidance on Create. Character Creator continues storing original identity references and reference-angle roles; it does not store realism settings.

## Verification and changed files

Earlier offline routing verification: **220 passed in 1.36s**. This historical checkpoint preceded the authorised private installation and live checks below.

This follow-up changes `qt_cockpit.py`, `genesis/generation_pipeline.py`, `genesis/qt_ui/MainPremiumLinux.qml`, `tests/test_pose_identity_routing.py`, `tests/test_runpod_lora_wiring.py`, adds `tests/test_i2i_realism.py`, and updates only positive prompt text in these existing workflow files:

- `STAGE_1_PHR00T_POSE.json`
- `PHR00T_QWEN_RAPID_V19_AIO.json`
- `PHR00T_QWEN_RAPID_V23.json`
- `KLEIN9B_REMOTE.json`
- `GENESIS_MIRACLEIN_9B_EDIT.json`
- `GENESIS_PORNMASTER_9B_EDIT.json`
- `GENESIS_DARKBEAST_9B_IDENTITY.json`

Original checkout remains dirty and uncommitted. The GitHub draft is built from a separate tested snapshot and includes dependencies needed by the earlier routing fix; unrelated original working-tree changes are excluded.

## Review tightening

The draft preserves GENESIS_AISHA_9B_TEST.json exactly as it exists on GitHub main, including its editor layout and face-swap route. The required base-generation graph lives separately in GENESIS_AISHA_9B_T2I.json. Removed inherited font/control-size changes, unrelated FLUX.1 catalog changes and startup auto-connect changes. Base 9B graph defaults now match its profile even when no controls are supplied. Review snapshot: 213 tests passed in 1.36s. The original local working-tree diff and status were checked and stayed unchanged during review.

## Character A and independent finishing

Character Creator stores one active identity, with untouched Primary/Front, ¾ Left, ¾ Right, Profile, Upper Body and Full Body references, replace/delete, thumbnails and a zoomable preview. Extra Phr00t identity angles are sent only when the connected conditioning node actually supports extra inputs. Pose images remain composition references, not a second stored identity.

Post-generation Keep/Save, Refine, Face Lock, Upscale 2×/4× and Full Finish operate on the selected saved result. Face Lock works without Refine and reads the untouched identity master. Every result retains its source/master association in history; comparison and rejection preserve files. Stage 2 uses installed compatible models, with Juggernaut/Lustify excluded. Face Lock and Upscale are gated by actual nodes and weights. Refine detail LoRAs stay family-gated; RefControl is not a finishing detail adapter.

## Imported pose source priority

Declared source metadata, original index prompt fields and same-name JSON sidecars take precedence over Grok fallback text. Exact model variants keep Phr00t v19/v23 distinct. Source text is not combined with Grok text. Pack settings and triggers require an explicitly matching model/family. Numeric settings are bounded and fixed FLUX scheduler behavior is retained. Phr00t keeps zeroed negative conditioning; SDXL retains its own negative conditioning. The executable RefControl route exclusively supplies its exact ordering trigger after input/compatibility checks.

Attribution is carried to the UI. The current 486-row imported indexes contain only file/category/resolution metadata, so these rows do not claim unavailable tested source prompts/settings. The current source library is untouched. Imported preset sections reference the existing control paths once, including existing multi-person categories, without copying pose files.

## User 8189 installation and verification

The user explicitly authorised installation of missing Face Lock and Upscale components. New custom-node code, dependencies, CodeFormer/Inswapper and UltraSharp weights reside under a private `/workspace/genesis-8189` base/environment. Existing model paths are retained as references. OpenPoseXL2 was also missing and was installed for the existing SDXL pose route. Only the user ComfyUI process on 8189 is restarted; the pod is not stopped/recreated and 8188 is never addressed by generation or restart commands.

The Phr00t GGUF route can use its already-installed matching Qwen 2.5 VL 7B safetensors encoder through the GGUF loader; it cannot fall back to Klein’s Qwen 3 encoder. The GGUF project documents support for both formats: https://github.com/city96/ComfyUI-GGUF . ReActor source: https://github.com/Gourieff/ComfyUI-ReActor . OpenPoseXL2 source: https://huggingface.co/thibaud/controlnet-openpose-sdxl-1.0 .

A neutral geometric refinement executed successfully on 8189 (prompt `2d2c69db-9383-42a2-9c31-e23368cdcbb4`). No output was opened or evaluated. Neutral finishing integration checks and the final catalogue check are recorded in the task verification report. Tests validate graph execution and routing, not photographic/face quality.

The saved public proxy address returned 403. With explicit user approval, the existing GENESIS public SSH key was registered, and a local tunnel forwards 18189 exclusively to remote 8189. An optional launcher helper maintains that route; it does nothing for other configured endpoints. The previous tunnel template’s 8188 target was corrected to 8189. No keys, credentials, pod addresses or machine-local connection file are published in this draft.

The original checkout remains dirty and uncommitted. GitHub uses a separate tested snapshot; no merge occurs.

## Final verification

Final focused suites: original checkout **272 passed in 1.44s**; isolated review snapshot **272 passed in 1.42s**. Neutral live checks passed: SDXL Refine; independent Upscale 2× (128→256); independent Upscale 4× (128→512); and Face Lock→Upscale 2×, preserving input/master bytes and intermediate files. The neutral Face Lock input contains no face, so this confirms execution rather than facial similarity. Regression tests cover all seven finishing combinations. No explicit images were generated, opened or evaluated.

The final user backend exposes **1,358 node classes, with none of the original 1,337 classes missing**, and six installed runnable source-image profiles: Aisha 9B, Miraclein 9B, two installed SDXL mixes, Phr00t v19 Q8 and Phr00t v23 Q8. Other configured variants remain filtered when absent; this does not claim every variant is installed or live-tested. Brother’s process identity was checked around each user-only restart and remained unchanged.
