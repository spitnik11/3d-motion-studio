# Environment Audit — Phase 0

_Audited 2026-08-19. Read-only inspection; nothing installed or changed._

## Toolchain (present)

| Tool | Version | Notes |
|------|---------|-------|
| Node | v24.16.0 | |
| npm  | 11.4.1  | |
| Python | 3.10.11 | System Python; project uses its own venv |
| git  | 2.49.0 | |
| ffmpeg | 8.0.1 | Needed for sequence/video export |
| gh CLI | 2.95.0 | Authed as `spitnik11` |

## Blender — **MISSING (blocking)**

No `blender.exe` found: not on PATH, not in `Program Files`/`Program Files (x86)`,
not in Steam, not on `Z:`. The entire manual-first workflow (Phases 3–19) depends
on Blender. **Action before Phase 3:** install Blender 5.2 LTS
(https://www.blender.org/download/releases/5-2/). Phases 1–2 do not need it.

## ComfyUI

- Production install: `Z:\codex app\ComfyUI`, listening on **:8188** (do not touch).
- Model tree present under `.../models`: `checkpoints`, `controlnet`, `loras`,
  `clip`, `vae`, `diffusion_models`, `rmbg`, `controlnet`, etc.
- **`controlnet-openpose-sdxl-1.0.safetensors` present** — the key adapter for the
  PoseBundle → Comfy path (Phase 18). Also `controlnet-canny-sdxl-1.0`, `sdpose_wholebody`.
- Style checkpoints (Illustrious / Pony / Anima / Z-Image / Krea) not enumerated in
  Phase 0; located per-adapter in Phase 18. `checkpoints/` currently holds mostly
  placeholders — real style models live elsewhere / to be discovered, not redownloaded.

## Sibling apps (do NOT modify)

- `Z:\codex app` — Z-Image Studio backend + production ComfyUI. **:3199 listening.**
- `Z:\frame-motion-studio` — Frame Motion Studio. Not running at audit time
  (memory says server :3200). PoseBundle consumer (Phase 17).

## Ports

See `ports.md`. Targets `:8190` (3D Comfy) and `:3201` (3D Motion Studio) are **free**.

## Gate

Existing systems unaffected — no installs, no config changes. PASS.
