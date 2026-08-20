# AI Generators — install status & unblock steps

Audited 2026-08-19 on the RTX 5070 (Blackwell, **sm_120**), torch 2.13.0+cu130, py3.13,
**no MSVC / no CUDA toolkit** on PATH. Everything heavy lives on **Z:** (`Z:/ai-repos`,
`Z:/ai-envs`, `Z:/ai-models`, `Z:/ai-assets`). Repos are cloned; envs staged.

## ✅ Live now (installed + verified)

| Feature | Env | Status |
|---|---|---|
| **Stable Fast 3D** image→3D (Phase 20) | `Z:/ai-envs/stable-fast-3d` (py3.13, torch 2.13+cu130) | **LIVE on the 5070** — real textured `mesh.glb` (~3.7k verts) from an image in ~3s, peak 6.2 GB VRAM. Full pipeline generate→stage→validate→approve→registry. Test: `tests/test_stable_fast_3d.py`. Weights (5.5 GB) on `Z:/ai-models/hf`. |
| **SPAR3D** image→3D (Phase 20) | same env (+ CLIP, AlphaCLIP, transparent-background) | **LIVE** — higher-detail `mesh.glb` (~13k verts) + point cloud, ~10.5 GB peak. Same provider path. Note: `transparent-background` downloads a bg-removal model on first run (one-time). Test: same file. |
| **Driving-video pose extraction** (Phase 29) | `Z:/ai-envs/driving-video` (mediapipe 0.10.14) | **Working** — video/image → canonical joints; enabled via `config/local.json`. Test: `tests/test_driving_video.py`. |
| **Real character import** (VRM + GLB) | Blender VRM add-on v4.5.0 | **Working** — CC0 VRoid VRM + CC-BY Khronos GLB import; `vroid` SemanticRig family. Test: `tests/test_real_assets.py`. |

### The compile recipe that cracked it (RTX 5070 / sm_120)
VS Build Tools + CUDA 13.3 installed. Build CUDA extensions with:
`export CL="/Zc:preprocessor /std:c++17"` + `CUDA_HOME=.../v13.3` +
`pip install --no-build-isolation ./texture_baker ./uv_unwrapper`. Env is **py3.13**;
deps relaxed to cp313 wheels (numpy 2.2 / transformers 4.46 / gpytoolbox 0.3.7). HF
weights: user `huggingface-cli login` (token global), download with `HF_HUB_CACHE=Z:/ai-models/hf`.

## ⛔ Blocked heavy generators (cloned, not runnable here)

Each is blocked on factors outside code effort. The gated providers already degrade
gracefully (disabled → refuse, never crash), so the app is unaffected.

| Repo | Blocker(s) | To unblock |
|---|---|---|
| ~~stable-fast-3d~~ | **DONE — now LIVE** | ✅ |
| ~~stable-point-aware-3d / SPAR3D~~ | **DONE — now LIVE** (AlphaCLIP installed `--no-build-isolation`) | ✅ |
| **UniRig** (Phase 23) | `flash_attn` + `spconv` + `torch_scatter/cluster` all need compile; no cu130 wheels; `bpy==4.2` conflicts w/ Blender 5.2 | build tools + a torch-geometric build matched to cu130 (may need source builds) |
| **momask-codes** (Phase 28) | pins **torch 1.12.0+cu113** → no Blackwell kernels; ancient numpy/matplotlib pins | port to torch ≥2.7; CPU-only fallback possible but slow |
| **HY-Motion-1.0** (Phase 28) | pins **torch 2.5.1** → no sm_120 kernels; needs Autodesk `fbxsdkpy` | bump to torch ≥2.7/cu128 + FBX SDK |

### The two levers that unblock the most
1. **Your Hugging Face token** (I won't request/enter it) → unlocks Stable Fast 3D & SPAR3D weights.
2. **Install VS Build Tools + CUDA Toolkit 13** (~8–10 GB, installs to C: — system SDKs
   can't go on Z:) → enables the CUDA/C++ compiles.

MoMask/HY-Motion additionally need a **torch upgrade/port** for Blackwell — a real
code effort, not a config change.

## Provider wiring (already in place)

`generators/mesh/providers.py`, `generators/rig/providers.py`,
`generators/motion/providers.py`, `generators/blender_mcp.py` — all gated on
`capabilities.*`. Flip a flag in `config/local.json` once a model is installed and the
provider goes live (that's exactly how driving-video was switched on).
