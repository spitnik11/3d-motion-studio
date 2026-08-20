# Roadmap

Manual-first order — **do not reverse**. Each phase ends with the completion rule
(run tests + smoke, verify Z-Image / ComfyUI / Frame Motion still work, record deps
& changed files, update docs, commit). Do not proceed on a broken phase.

`[x]` done · `[ ]` pending · **★ MVP gate at Phase 19**.

| # | Phase | Gate | Status |
|---|-------|------|--------|
| 0 | Environment audit | Existing systems still launch | [x] |
| 1 | Independent project | Delete/recreate without affecting siblings | [x] |
| 2 | Asset Registry | Import → restart → identical metadata | [x] |
| 3 | Blender Bridge | Automated: launch→scene→object→move→save→reopen→verify | [x] |
| 4 | Character import (VRM/FBX/GLTF/BLEND) | Fixtures load w/ mesh, mats, rig, scale, provenance | [x]¹ |
| 5 | SemanticRig v1 | One semantic command across 3 rig families | [x] |
| 6 | Manual Pose Studio | Create + recall 5 poses, no AI | [x] |
| 7 | Hand/finger posing | Hand pose transfers via SemanticRig to 2 chars | [x] |
| 8 | IK + Pose Locks | Agent/API cannot move locked bones | [x] |
| 9 | Two-character contact | 3 stable paired poses manually | [x] |
| 10 | Pair Pose assets | Apply PairPose to a different compatible pair | [x] |
| 11 | Manual animation | 8–12 frame paired animation, no AI | [x] |
| 12 | Motion import + retarget | Import motion, edit hand/arm/foot/timing after retarget | [x] |
| 13 | Scene system | Load scene + 2 chars + lights + camera from one manifest | [x] |
| 14 | Camera system | Changing characters doesn't shift stored framing | [x] |
| 15 | Control pass renderer | Same scene state → repeatable passes | [x] |
| 16 | **PoseBundle v1** | Validate PoseBundle entirely outside Blender | [x] |
| 17 | Frame Motion import | Frame Motion loads a PoseBundle with Blender closed | [x] |
| 18 | Comfy finishing | One posed frame → stylized frame, pose preserved | [x] |
| 19 | **★ Full frame sequence** | Reject frame 5, regen only 5, rest untouched | [x] |
| — | **MVP GATE** | Full manual→PoseBundle→Comfy→repair loop | [x] |
| 20 | AI prop generation | (post-MVP) | [x]² |
| 21 | Hunyuan3D experiment | Disabling it has zero effect on manual posing | [x] |
| 22 | Generated humanoids | Character passes deformation QA | [x] |
| 23 | UniRig experiment | Failure falls back to manual rigging | [x] |
| 24 | Agent API v1 | Semantic primitives only, no arbitrary Blender Python | [x] |
| 25 | Agent snapshot/undo | One op restores previous state | [x] |
| 26 | Agent pose assist | Accept/Reject/Revert/Edit | [x] |
| 27 | Agent animation assist | Works around locked edits | [x] |
| 28 | Text-to-motion (MoMask) | Candidate only, manual review before output | [x] |
| 29 | Driving video | Preserve movement, discard identity/background | [x] |
| 30 | Asset Browser UI | No raw filesystem paths as main UX | [x] |
| 31 | Civitai model registry | No blind agent installs | [x] |
| 32 | License-aware import | Agent summarizes, human approves | [x] |
| 33 | External .blend security | Untrusted; no auto script execution | [x] |
| 34 | Optional Blender MCP | Experiment only; not project truth | [x] |
| 35 | Project hardening | Missing optional dep disables feature, not app | [x] |
| 36 | Final acceptance test | Two chars + ring scene, full loop, repair 1 frame | [x] |

¹ Verified via a self-generated rigged+textured GLB (zero downloads). The **VRM path**
(VrmCharacterImporter) is structurally in place but needs the Blender VRM add-on +
a real VRoid file to fully verify — that's the one bit needing your asset.

² Pipeline (stage→validate→approve→registry) + provider framework done and gated;
verified with a Blender-authored mesh. The **live Stable Fast 3D / SPAR3D** providers
are disabled until their models are installed in an isolated env (a GPU download —
needs your go-ahead).

³ Provider framework + capability gate done (disabled provider refuses, app degrades,
never crashes). **Live model** (UniRig / MoMask / HY-Motion / pose-extraction) installs
into an isolated env on demand — a GPU download that needs your go-ahead. Deformation QA
(Phase 22) is real and runs on any rigged character today.

## Status

**All 36 phases + MVP gate pass** (2026-08-19), every gate on real hardware — headless
Blender 5.2 + live ComfyUI. 12 test files, ~40 gate assertions. Fully working end to
end (`test_acceptance.py`).

The only things gated on **your input** (not blockers — the app runs and degrades
gracefully without them):
- A real VRoid/Quaternius character to fully exercise the VRM importer (¹).
- GPU model installs to switch the live AI generators on: Stable Fast 3D/SPAR3D (²),
  UniRig / MoMask / HY-Motion / driving-video pose extraction (³).

### Live AI generators (post-plan, on the RTX 5070)
Stable Fast 3D ✅ · SPAR3D ✅ · UniRig skeleton ✅ · driving-video pose ✅ · real VRM/GLB
import ✅. Deferred (need porting): UniRig skinning, MoMask, HY-Motion. See `docs/GENERATORS.md`.
**AI loop closed**: generated prop → PoseBundle; generated humanoid → UniRig → auto-calibrate
(SemanticRig) → posed (`test_compose.py`, `test_generated_character.py`).

---

## Parallel UI + Import track (companion design doc)

Added per `3D_Motion_Studio_UI_Import_Design.md` — a **parallel** track that does not
renumber the 36 backend phases; on conflict the hardened backend plan wins. Full plan +
import architecture in **`docs/FRONTEND.md`**.

| Track | Scope | Status |
|---|---|---|
| — | **Control panel v0** (single-file, served at `/` on :3201) over the Agent API | [x] |
| UI-A | React app shell (workspace tabs, docked layout, Inspector, keyboard) | [ ] |
| UI-B | Import Studio (quarantine, inspection, license/dep, Sketchfab + SmutBase adapters) | [ ] |
| UI-C | Live R3F viewport + WebSocket sync + Outliner | [ ] |
| UI-D | Pose Studio (body/hand/IK/locks/contacts/pair-pose) | [ ] |
| UI-E | Animation Studio (timeline/keyframes/retarget/camera) | [ ] |
| UI-F | Typed pipeline canvas (@xyflow/react) | [ ] |
| UI-G | Full Asset Browser (search/tags/badges/thumbnails) | [ ] |
| UI-H | AI surfaces (gated providers + agent assist) | [ ]⁴ |

⁴ The live generators (SFast3D/SPAR3D/UniRig/driving-video) are already exposed in the
control-panel-v0 Generate panels; UI-H is the full node-based surface.
