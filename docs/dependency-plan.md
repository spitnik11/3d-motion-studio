# Dependency Plan

Discovery order for every dependency (per the plan's completion rule):

```
discover → verify missing → check compatibility → install in isolated env
```

## Present (reuse, do not reinstall)

Node 24, npm 11, Python 3.10.11, git, ffmpeg, gh CLI, production ComfyUI + models.

## To install, in order of need

| When | Dependency | Where | Notes |
|------|-----------|-------|-------|
| Before Phase 3 | **Blender 5.2 LTS** | system | Blocking for manual workflow. Test compat first. |
| Phase 4 | Blender VRM add-on | Blender extensions | https://extensions.blender.org/add-ons/vrm/ — no custom VRM parser. |
| Phase 5+ | Rigify | Blender (bundled add-on) | Enable, don't install. |
| Phase 4 (Tier B) | MPFB | Blender extensions | Optional human proxies. |
| Phase 2+ | Python deps (FastAPI/etc.) | project **venv** | Never the Blender Python env. |
| Phase 1 | control-ui deps | `apps/control-ui` npm | React. |

## Isolation law

- Blender Python env and the project venv stay separate.
- AI mesh/motion generators (Stable Fast 3D, Hunyuan3D, MoMask, UniRig) get
  **dedicated environments or the `:8190` Comfy** — never merged into Blender's Python.
- Every optional dep missing ⇒ feature disables gracefully, app still runs.

## Not installing now

Nothing beyond the scaffold. No dependency is installed merely because the plan
mentions it — only on the phase that needs it, after the discovery check above.
