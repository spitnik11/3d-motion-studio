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
| 3 | Blender Bridge | Automated: launch→scene→object→move→save→reopen→verify | [ ] |
| 4 | Character import (VRM/FBX/GLTF/BLEND) | Fixtures load w/ mesh, mats, rig, scale, provenance | [x]¹ |
| 5 | SemanticRig v1 | One semantic command across 3 rig families | [x] |
| 6 | Manual Pose Studio | Create + recall 5 poses, no AI | [ ] |
| 7 | Hand/finger posing | Hand pose transfers via SemanticRig to 2 chars | [ ] |
| 8 | IK + Pose Locks | Agent/API cannot move locked bones | [ ] |
| 9 | Two-character contact | 3 stable paired poses manually | [ ] |
| 10 | Pair Pose assets | Apply PairPose to a different compatible pair | [ ] |
| 11 | Manual animation | 8–12 frame paired animation, no AI | [ ] |
| 12 | Motion import + retarget | Import motion, edit hand/arm/foot/timing after retarget | [ ] |
| 13 | Scene system | Load scene + 2 chars + lights + camera from one manifest | [ ] |
| 14 | Camera system | Changing characters doesn't shift stored framing | [ ] |
| 15 | Control pass renderer | Same scene state → repeatable passes | [ ] |
| 16 | **PoseBundle v1** | Validate PoseBundle entirely outside Blender | [ ] |
| 17 | Frame Motion import | Frame Motion loads a PoseBundle with Blender closed | [ ] |
| 18 | Comfy finishing | One posed frame → stylized frame, pose preserved | [ ] |
| 19 | **★ Full frame sequence** | Reject frame 5, regen only 5, rest untouched | [ ] |
| — | **MVP GATE** | Full manual→PoseBundle→Comfy→repair loop | [ ] |
| 20 | AI prop generation | (post-MVP) | [ ] |
| 21 | Hunyuan3D experiment | Disabling it has zero effect on manual posing | [ ] |
| 22 | Generated humanoids | Character passes deformation QA | [ ] |
| 23 | UniRig experiment | Failure falls back to manual rigging | [ ] |
| 24 | Agent API v1 | Semantic primitives only, no arbitrary Blender Python | [ ] |
| 25 | Agent snapshot/undo | One op restores previous state | [ ] |
| 26 | Agent pose assist | Accept/Reject/Revert/Edit | [ ] |
| 27 | Agent animation assist | Works around locked edits | [ ] |
| 28 | Text-to-motion (MoMask) | Candidate only, manual review before output | [ ] |
| 29 | Driving video | Preserve movement, discard identity/background | [ ] |
| 30 | Asset Browser UI | No raw filesystem paths as main UX | [ ] |
| 31 | Civitai model registry | No blind agent installs | [ ] |
| 32 | License-aware import | Agent summarizes, human approves | [ ] |
| 33 | External .blend security | Untrusted; no auto script execution | [ ] |
| 34 | Optional Blender MCP | Experiment only; not project truth | [ ] |
| 35 | Project hardening | Missing optional dep disables feature, not app | [ ] |
| 36 | Final acceptance test | Two chars + ring scene, full loop, repair 1 frame | [ ] |

¹ Verified via a self-generated rigged+textured GLB (zero downloads). The **VRM path**
(VrmCharacterImporter) is structurally in place but needs the Blender VRM add-on +
a real VRoid file to fully verify — that's the one bit needing your asset.

## Immediate next step

Install **Blender 5.2 LTS** (only blocking dependency), then start Phase 2 (Asset
Registry) — Phase 2 needs no Blender, so it can begin in parallel with the install.
