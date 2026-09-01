# Milestone 1 Media Viewer Consolidation Plan

Status: analysis only. No viewer has been removed, renamed, replaced, or wired
into the cockpit as part of Milestone 1.

## Inventory

The repository contains 18 viewer implementations spanning four overlapping
families:

- `media_viewer.py`: original PyQt gallery with asynchronous thumbnails.
- `media_viewer_v03.py` through `media_viewer_v09.py`: cumulative face,
  tagging, export, analytics, filtering, collection, cloud, backup, and sharing
  experiments.
- `media_viewer_v10.py`, `media_viewer_v10_fixed.py`, and
  `media_viewer_v10_working.py`: performance-focused rewrites.
- `simple_viewer*.py` and `media_viewer_pyqt6_face.py`: alternate minimal and
  face-enabled viewer experiments.

The active Tk cockpit does not currently import any of these. Its Media button
opens Jellyfin Desktop, while its Photo Organiser is implemented directly in
`main.py`.

## Findings

1. `media_viewer_v09.py` has the broadest feature surface: face recognition,
   tags, timeline, analytics, filtering, smart collections, backup, cloud
   export, and sharing. It is the strongest functional reference, but several
   dependencies still need canonical-database migration and runtime tests.
2. `media_viewer_v10.py` and `media_viewer_v10_fixed.py` cannot import because
   they reference the missing `genesis.lazy_loader` module.
3. `media_viewer_v10_working.py` has no missing local import and is the safest
   performance-reference implementation, but it omits much of v09's feature
   surface.
4. `media_viewer.py` expects an older thumbnail/database representation and is
   not compatible with the canonical schema without an adapter.
5. Face detection is duplicated both in viewers and in
   `genesis.face_detection.detector`; inline copies should eventually delegate
   to the package service.
6. Launch scripts currently point to `simple_viewer_working.py` and
   `simple_viewer_faces.py`, while `genesis_status.py` recommends the broken
   `media_viewer_v10.py`. There is no single supported entry point.
7. The Python environments are fragmented: `.venv` can import the Tk cockpit
   and face stack but lacks PyQt6/rembg; `genesis_env` has PyQt6 but lacks a
   working face-recognition model package and `imagehash`.

## Recommended target architecture

Do not select a viewer solely by filename/version. Build one supported
`genesis.media` package from existing proven pieces:

- Use the v09 feature surface as the functional acceptance checklist.
- Use `media_viewer_v10_working.py` and `optimized_cache.py` as performance
  references.
- Use the canonical `genesis.database` connection/session API.
- Use `genesis.face_detection.detector` through an adapter rather than copying
  face logic into the UI.
- Expose a single `launch_media_viewer()` boundary for the Tk cockpit and launch
  scripts.
- Keep Jellyfin as a separate media-system integration; do not replace its Home
  or AI cockpit action with the photo-library viewer.

This is consolidation by extracting and wiring existing behavior, not a new
viewer rewrite.

## Proposed approval-gated sequence

1. Define an automated feature matrix and smoke tests for v09 and
   `v10_working` against a temporary canonical database.
2. Repair shared module/schema incompatibilities without changing entry points.
3. Add a thin supported facade that selects the proven implementation.
4. Wire a separate "Genesis Photo Library" action into the cockpit.
5. Update launch scripts and status guidance only after the supported facade
   passes functional and performance checks.
6. Preserve all historical viewer files through at least one release. Any later
   archival, relocation, or deletion requires explicit user approval.

## Approval required before Milestone 2 implementation

Approval is required to designate `media_viewer_v09.py` plus
`media_viewer_v10_working.py` as the consolidation sources and to change any
current viewer launch target. No destructive cleanup is proposed.
