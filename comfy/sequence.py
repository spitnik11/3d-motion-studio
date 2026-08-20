"""Full frame sequence + selective regeneration — Phase 19.

Finish every frame of a PoseBundle through Comfy, track per-frame accept/reject
state, and regenerate ONLY rejected frames — leaving accepted frames' files byte-
for-byte untouched.
"""

from __future__ import annotations

import json
from pathlib import Path

from comfy.finish import finish_frame


def _state_path(out_dir) -> Path:
    return Path(out_dir) / "sequence.json"


def _frame_out(out_dir, f: int) -> Path:
    return Path(out_dir) / f"frame_{f:04d}.png"


def finish_sequence(client, sp, bundle_dir: str, out_dir: str, *, seed: int = 42,
                    frames=None) -> dict:
    bundle, out = Path(bundle_dir), Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((bundle / "manifest.json").read_text())
    frames = frames or manifest["frames"]
    state = {"frames": {}}
    for f in frames:
        fseed = seed + f
        res = finish_frame(client, sp, str(bundle / f"frame_{f:04d}"),
                           str(out / f"_tmp_{f:04d}"), seed=fseed)
        Path(res["stylized"]).replace(_frame_out(out, f))
        state["frames"][str(f)] = {"stylized": str(_frame_out(out, f)),
                                   "status": "pending", "seed": fseed}
    _state_path(out).write_text(json.dumps(state, indent=2))
    return state


def set_status(out_dir: str, frame: int, status: str) -> dict:
    """status in {'accepted','rejected','pending'}."""
    state = json.loads(_state_path(out_dir).read_text())
    state["frames"][str(frame)]["status"] = status
    _state_path(out_dir).write_text(json.dumps(state, indent=2))
    return state


def rejected_frames(out_dir: str) -> list[int]:
    state = json.loads(_state_path(out_dir).read_text())
    return [int(f) for f, v in state["frames"].items() if v["status"] == "rejected"]


def regenerate_frames(client, sp, bundle_dir: str, out_dir: str, frames_to_regen, *,
                      seed_offset: int = 1000) -> dict:
    """Re-run ONLY the given frames. Other frames' output files are never touched."""
    bundle, out = Path(bundle_dir), Path(out_dir)
    state = json.loads(_state_path(out).read_text())
    for f in frames_to_regen:
        new_seed = state["frames"][str(f)]["seed"] + seed_offset
        res = finish_frame(client, sp, str(bundle / f"frame_{f:04d}"),
                           str(out / f"_regen_{f:04d}"), seed=new_seed)
        Path(res["stylized"]).replace(_frame_out(out, f))
        state["frames"][str(f)].update(status="regenerated", seed=new_seed)
    _state_path(out).write_text(json.dumps(state, indent=2))
    return state
