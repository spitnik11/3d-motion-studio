# Integration Boundaries

The deletion test governs this project: deleting `Z:\3d-motion-studio` must leave
Z-Image Studio, Frame Motion Studio, and production ComfyUI fully working.

## Hard rules

- **No existing app imports code from 3D Motion Studio.** Coupling is one-way, outbound.
- Do not modify `Z:\codex app` or `Z:\frame-motion-studio` to support this project.
- Production ComfyUI (`:8188`), PyTorch, CUDA, custom nodes, and model dirs are
  read-only. Reuse discovered models in place; never redownload existing families.

## The one integration point

**PoseBundle** (Phase 16) is the only contract crossing into Frame Motion Studio.

```
3D Motion Studio ──(PoseBundle, files only)──▶ Frame Motion Studio ──▶ ComfyUI
```

- PoseBundle is plain files (PNG/EXR/JSON). Frame Motion parses it **without Blender**.
- Blender internals are never exposed across the boundary.
- Phase 17 adds a `PoseBundleImporter` to Frame Motion — the smallest possible change,
  and the only edit this project may make to a sibling app.

## Comfy usage

Read model info from `:8188` via `object_info`; run finishing jobs against it.
If experimental 3D nodes are ever needed, stand up a separate Comfy on `:8190` —
never install them into `:8188`.
