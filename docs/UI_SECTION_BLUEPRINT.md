# GENESIS c0ckpit — Windows UI Section Blueprint

Status: implementation reference for `windows-build`.

## Global shell

- Dark graphite / near-black desktop shell with antique-gold / bronze interaction accents and restrained cool-blue status accents.
- Stable left navigation: Home, Image Generation, Pose Library, Workflow Studio, Camera Hub, Media Tools, Entertainment, System Tools, Settings.
- Privacy-first: no Recent, Favourites, or Compare sections on the home screen.
- Keep GENESIS c0ckpit branding and the slogan `Keep walking Allan.`
- Content should dominate the workspace. Gold means selected, active, ready, or primary action rather than decorating every edge.
- Preserve functional bindings already present in QML: source loading, generation profiles, model/LoRA compatibility, workflow selection, output/progress state, pose selection, module actions.

## Image Generation — BestFaceSwap-style task flow

Reference intent: obvious first-use flow with professional advanced controls.

- Left task rail / compact setup column.
- Large source-image drop zone with click-to-browse, loaded thumbnail, Replace, Remove, and accepted-format state.
- Prompt and model/workflow selectors close to the source controls.
- Compatible LoRA selectors only; incompatible LoRAs hidden or disabled with explanation.
- Large result preview occupies the majority of the workspace.
- One dominant `GENERATE` action.
- Quality/aspect controls near Generate.
- Advanced inspector for CFG, steps, denoise, seed, stage toggles and workflow-specific settings.
- Visible progress, elapsed time, output folder, Open Result / Open Folder actions.

## Pose Library — Playbox-style visual catalogue

- Large thumbnail grid with fast browsing.
- Search plus category/filter chips.
- Badges for collection, model/workflow compatibility, quality and source type.
- Include the verified Full 70 preset pack and Curated 18 pack from the Windows data path; do not silently merge or rename collections.
- Source-image loader remains accessible from the pose workflow.
- Selecting a pose feeds Image Generation immediately.
- `Use Preset` / `Generate` actions should be direct and obvious.

## Workflow Studio — professional workflow editor

- Workflow/library browser on the left.
- Central workflow/node canvas.
- Right validation / compatibility inspector.
- Show selected model, LoRAs, workflow readiness, missing assets, validation state and test controls.
- Keep the same GENESIS shell; do not visually resemble a separate application.

## Media Viewer — PowerDVD-style media-first browser

- Left media categories / folder sources.
- Breadcrumb path across the top.
- Search and sort.
- Large image/video thumbnail grid.
- Selected media opens inside GENESIS.
- Persistent image/video controls where applicable.
- Context actions: Enhance, Upscale, Background Remove, Canvas Editor, Duplicate Finder, Face Organiser.

## Face Organiser — ACDSee People interaction model

People overview:
- Named / Unnamed tabs.
- One card per identity with representative face thumbnail, name and face count.

Person detail:
- Identity header and back navigation.
- Confirmed faces grid.
- Separate `Suggested Faces — Is this [name]?` area.
- Approve / Reject suggestions.
- Merge People, Split Person, Rename, Ignore Face, Show Source Image.
- Scan/index originals in place; do not automatically move source files.

## Duplicate Finder — AllDup split verification workspace

- Duplicate groups/list on the left with expandable groups and checkboxes.
- Filename, folder, size, dimensions, type and similarity score.
- Large selected preview and metadata on the right.
- Compare 2–4 candidates side by side with zoom.
- Detection modes: exact hash, visually similar, same-name, resized / near-duplicate.
- Safe actions: Keep Best, Move Extras, Delete Selected, Exclude Folder.
- Never auto-delete; require clear confirmation / recovery path.
- Footer: groups, files, reclaimable space, scan progress.

## Enhance / Upscale / Background Remover — batch editor workspace

Reference intent: MadPeel-style structure, GENESIS visual language.

- Tool rail left: Background Remove, Enhance, Upscale.
- Very large centre preview.
- Original / Result toggle and before/after comparison.
- Right settings inspector changes with active tool.
- Bottom batch strip with Pending, Processing, Done, Failed and Edited states.
- Apply Settings to All, Process All, Save Current, Save All.
- Background Remove options: transparent / solid / custom background, edge refinement, optional shadow.
- Show progress and elapsed time per item and for the batch.

## Canvas Editor — Photoshop-style spatial architecture

- Central canvas with checkerboard transparency, zoom/pan, optional rulers/guides.
- Left vertical tools: Select, Move, Crop, Rotate, Resize, Brush/Erase, Text, Shape, Background Remove, Cutout/Mask.
- Top contextual controls: dimensions, aspect lock, rotation, opacity, feathering, alignment.
- Right inspector: Properties, Adjustments, Layers.
- Layers: visibility, order, rename, duplicate, delete, opacity, flatten, merge.
- Multiple document tabs.
- Floating quick bar: Select Subject, Remove Background, Enhance, Upscale, Adjust, Duplicate, Delete.
- Custom canvas sizes/presets, transparent PNG cutouts, resize/rotate/reposition, export.

## Camera Hub

- Own main navigation item.
- Large live preview / camera tile area.
- Device and stream inspector on the right.
- Source selection, status, reconnect and launch controls kept visible without turning the page into a settings form.

## Entertainment

- Group Jellyfin / local media playback and SillyTavern under Entertainment.
- Media-first visual layout consistent with the GENESIS shell.
- Avoid wallpaper-heavy chrome that competes with content.

## Interaction standards

- Every exposed control must have a working hover, pressed, selected, disabled and focus state.
- Loaded images must visibly change state; do not leave the user wondering whether a source was accepted.
- Errors should say what is missing and how to fix it.
- Processing should expose progress, elapsed time and clear completion state.
- Preserve selections when switching presets where logically safe.
- Advanced implementation details stay behind `Advanced`; primary flow should read as `Load image → choose look/pose → Generate`.

## Verification gate

Do not call the Windows build finished until:

1. QML loads cleanly.
2. Core tests pass on Windows.
3. Whole-suite collection no longer crashes on optional face dependencies.
4. Source-image selection, pose selection, model/LoRA compatibility, output-folder actions and generation validation are smoke-tested.
5. No dead buttons remain on exposed production pages.
