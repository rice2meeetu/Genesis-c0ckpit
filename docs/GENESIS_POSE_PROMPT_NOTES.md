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

Local focused suite: **220 passed in 1.36s**. Compilation and `git diff --check` passed. Tests are offline and inspect text/graph routing only. Neither ComfyUI port was contacted or restarted.

This follow-up changes `qt_cockpit.py`, `genesis/generation_pipeline.py`, `genesis/qt_ui/MainPremiumLinux.qml`, `tests/test_pose_identity_routing.py`, `tests/test_runpod_lora_wiring.py`, adds `tests/test_i2i_realism.py`, and updates only positive prompt text in these existing workflow files:

- `STAGE_1_PHR00T_POSE.json`
- `PHR00T_QWEN_RAPID_V19_AIO.json`
- `PHR00T_QWEN_RAPID_V23.json`
- `KLEIN9B_REMOTE.json`
- `GENESIS_MIRACLEIN_9B_EDIT.json`
- `GENESIS_PORNMASTER_9B_EDIT.json`
- `GENESIS_DARKBEAST_9B_IDENTITY.json`

Original checkout remains dirty and uncommitted. The GitHub draft is built from a separate tested snapshot and includes dependencies needed by the earlier routing fix; unrelated original working-tree changes are excluded.
