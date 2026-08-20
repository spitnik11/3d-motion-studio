# 3D Motion Studio

Manual-first, AI-assisted 3D character posing and animation. Builds structurally
accurate poses/animations in Blender, renders control passes, and exports
**PoseBundles** to Frame Motion Studio → ComfyUI for stylized finishing.

**The app must remain fully functional with every AI component disabled.**

```
Character + Scene + Manual Pose + Manual Animation
        → Blender → Control Passes → PoseBundle
        → Frame Motion Studio → ComfyUI
```

AI (mesh gen, auto-rig, text-to-motion, agent posing) only accelerates this — never
replaces the manual path.

## Boundaries

Standalone. Deleting `Z:\3d-motion-studio` leaves Z-Image Studio, Frame Motion
Studio, and production ComfyUI (`:8188`) working. No sibling app imports from here.
The only outbound contract is the **PoseBundle** (files only; no Blender needed to
read it). See [`docs/integration-boundaries.md`](docs/integration-boundaries.md).

## Status

- **Phase 0 — Environment audit:** done. See [`docs/environment-audit.md`](docs/environment-audit.md).
- **Phase 1 — Independent project:** done (this scaffold).
- **Phase 2 — Asset Registry:** done. `server/registry/registry.py` (stdlib sqlite3,
  provenance + tri-state license perms, unknown = UNKNOWN). Gate test `tests/test_registry.py` passes.
- Next: install Blender 5.2 LTS (blocking for Phase 3+), then Phase 3 (Blender Bridge).

Roadmap and gates: [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Ports

App `:3201` · reuse production ComfyUI `:8188` · optional experimental 3D Comfy `:8190`.
See [`docs/ports.md`](docs/ports.md).

## Layout

`apps/control-ui` UI · `server/` API+jobs+registry · `blender/` addon+bridge+scripts ·
`characters/`·`motion/`·`comfy/` adapters · `generators/` AI mesh/motion/rig ·
`contracts/` schemas (PoseBundle) · `assets/` · `data/` · `outputs/`.
