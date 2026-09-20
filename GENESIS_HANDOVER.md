# GENESIS V3 — GPT/Work Mode Handover

Updated: 2026-09-19
Repository: `/home/rice2meetyou/Genesis-c0ckpit`
Branch: `main`
Checkpoint at handover creation: `268e2e0 docs: checkpoint model availability and GPU workflow audit`

## Purpose

This file is the canonical entry point when GENESIS work moves between ChatGPT sessions/accounts or Work mode.
Do not rely on chat history as project state. Read this file, the linked docs, Git status, and the live machine/repository before making changes.

## Start every takeover with

```bash
cd /home/rice2meetyou/Genesis-c0ckpit
git status --short
git log -5 --oneline
python3 -m pytest -q
```

Then read, in order:
1. `docs/CURRENT_STATE.md`
2. `docs/NEXT_TASKS.md`
3. `docs/IMAGE_GENERATION_AUDIT.md`
4. `docs/MODEL_LORA_COMPATIBILITY.md`
5. `docs/KLEIN_9B_KV_RX9060XT_PROFILE.md`
6. `docs/GENESIS_RESUME.md`

## Handoff protocol

Before switching GPT/account, update `docs/CURRENT_STATE.md` and `docs/NEXT_TASKS.md`.
Record what was actually changed/tested; never claim a render, UI behavior, service state, or compatibility result without verification.
Commit coherent milestones when appropriate. Never discard unrelated dirty-tree changes just to make Git clean.
The next GPT should begin by reconciling these docs with live Git/machine state.

## Critical preservation rules

- GENESIS main project only; do not mix unrelated branches/projects.
- Preserve user files/models and existing workflows. No model downloads/deletions/moves without explicit reason/approval.
- Back up risky edits and avoid destructive Git reset/clean.
- Treat installed, metadata-compatible, graph-valid, and render-tested as different states.
- Model/LoRA stacking must be compatibility-aware and individually weighted; do not infer compatibility from filenames alone.
- Preserve the known-good ROCm environment unless a measured reason justifies changing it.
- Dirty service/artwork files listed in CURRENT_STATE are intentional until reconciled.

## Current focus

The active priority is the Image Generation workspace and its real model/workflow inventory:
model selection -> compatible ordered LoRA slots -> per-LoRA strengths -> workflow/preset/pose routing -> source/reference handling -> preview -> generation.
The Pose Library page itself is secondary; its data should primarily serve Image Generation.

## Switching accounts

This repository is the shared state. Account A works, updates the checkpoint, and stops at a coherent boundary; Account B reads the checkpoint plus live repo and continues.
That makes back-and-forth handoff practical even though separate ChatGPT accounts do not share chat memory automatically.
