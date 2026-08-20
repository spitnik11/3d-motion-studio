# Frontend & Import Plan (companion track)

Distilled from the companion design doc (`3D_Motion_Studio_UI_Import_Design.md`). This
is a **parallel UI track** — it does NOT renumber or replace the 36 backend phases.
**On any conflict, the hardened backend plan wins.**

## Invariants (non-negotiable)
- **Blender stays authoritative** for scene/armature/constraints/IK/animation/render.
  The frontend holds only viewport proxies, selection, layout, optimistic drag state.
- **Manual-first**: the app must be fully usable with every AI/Comfy/Frame-Motion piece
  OFF. AI is opt-in, gated, and degrades to "disabled node", never crashes.
- **Semantic ops only** over the public API — no arbitrary Blender Python from the UI.
- **All external assets are untrusted**: quarantine → inspect → no `.blend` autoexec →
  sanitize → license/provenance → AssetRegistry. Nothing bypasses the registry.
- **Don't touch** `Z:\codex app`, `Z:\frame-motion-studio`, or production ComfyUI/models.

## Target stack (evolution)
Now: single-file control panel served by the FastAPI Agent API (`apps/control-ui/`).
Planned: **React + TS + Vite**, **@react-three/fiber** (viewport), **@xyflow/react**
(typed pipeline graph), Zustand (UI state) + TanStack Query (server state) + WebSocket
(live Blender/job state). Electron only after web workflows stabilize.

## Current state
- ✅ **Control panel v0** (`apps/control-ui/control.html`, served at `/` on :3201):
  capabilities/service status, registry asset list, and operable **Generate** panels
  (mesh SFast3D/SPAR3D, UniRig skeleton, driving-video pose) over the live endpoints.
- ✅ Agent API surface: `/api/diagnostics`, `/api/capabilities`, `/api/assets`,
  `/api/scenes`, `/api/poses/apply`, `/api/contacts`, `/api/render/control-bundle`,
  `/api/generate/mesh|skeleton`, `/api/extract/pose`. Semantic-only; no arbitrary Python.
- ✅ Backend already supports the hard parts the UI will surface: SemanticRig (+ calibration),
  PoseLock, ContactConstraint, PairPose, control passes, PoseBundle, blend-security
  (`--disable-autoexec`), license gate, capabilities/degradation.

## UI implementation track (parallel to backend phases)

| Track | Scope | Aligns with backend | Gate |
|---|---|---|---|
| **UI-A** App shell | React shell, workspace tabs, docked resizable layout, Inspector, bottom panel, persisted layout, keyboard commands | Phase 1 | launches, layout restores, no Blender needed |
| **UI-B** Import Studio | local file + archive import, **quarantine**, package inspection, source metadata, license review, dependency detection, compatibility report, asset cards; then **SketchfabSourceAdapter** + **SmutBasePackageAdapter** | Phases 2/4/32/33 | import GLB + safe BLEND + archive pkg; metadata survives restart; no autoexec |
| **UI-C** Live viewport | R3F viewport, camera nav, selection, bone viz, gizmos, **viewport GLB proxy**, WebSocket sync, Outliner | Phase 3/5 | move semantic control → Blender solves → viewport reconciles → save/reload identical |
| **UI-D** Pose Studio | body pose, hand controls, IK targets, locks, contacts, pair-pose, pose library | Phases 6–10 | 2 chars, manual pose+fingers, stable contact, save PairPose, reload preserved |
| **UI-E** Animation Studio | timeline, keyframes, breakdowns, holds, motion import, retarget, camera UI | Phases 11–14 | 8–12f two-char anim, edit timing, save/reload identical |
| **UI-F** Pipeline Canvas | typed `@xyflow/react` graph (typed ports + validated edges), control-pass/PoseBundle/FrameMotion/style nodes, job state, error viz | Phases 15–19 | valid graph → PoseBundle; invalid blocked; regen one frame |
| **UI-G** Full Asset Browser | search/filter/tags/favorites/collections, source grouping, compatibility+license badges, lazy thumbnails | Phase 30 | 100+ assets browsable, no raw FS nav |
| **UI-H** AI surfaces | expose gated providers (SFast3D/SPAR3D/UniRig/driving-video live; Hunyuan/MoMask/HY-Motion deferred) + agent assist; unavailable → disabled node + reason | Phases 20–29 | unavailable provider disables its node only; manual unaffected |

## Import architecture (backend, `server/imports/` + `server/security/`)
`SourceAdapter` (Local/Archive/Sketchfab/SmutBase/VRoid/Quaternius/PolyHaven) →
`ImportCandidate` (provenance + license tri-state + detected files/formats/rig/scripts/
addons + warnings) → inspect → **security scan** (archive/blend/script scanners) →
license/provenance review → quarantine extract (`data/import-quarantine/{id}/`) →
Blender **safe import** (autoexec off) → sanitize → `TextureResolver` (relink into
`assets/library/{id}/`) → `DependencyDetector` → RigDetector → SemanticRig(+calibration)
→ deformation validation → AssetRegistry. Compatibility report persisted; status ∈
{READY, READY_WITH_WARNINGS, NEEDS_SETUP, FAILED_IMPORT, QUARANTINED}.

**Sketchfab** = online source provider (API, per-license download), not a Blender addon.
**SmutBase** = untrusted package (.7z/.zip/.rar; .blend/.fbx/.glb + textures + scripts +
Rigify/MHX/Diffeomorphic/MustardUI). Native support = *safely onboards the package*, not
runs it blindly. Compatibility add-ons live in an isolated **Blender Compatibility
Profile**, never a project-wide downgrade.

## Milestones
1. Manual MVP in the UI (2 chars + scene + big viewport + body/hand pose + visual
   contact + save/reload) — no AI required.
2. Import reliability (local GLB/FBX/VRM + safe BLEND + archive + Sketchfab + SmutBase →
   AssetRegistry + sanitized asset + provenance + compatibility report).
3. End-to-end manual animation → PoseBundle → Frame Motion → Comfy → per-frame repair.
Only then heavy AI-surface UI polish.
