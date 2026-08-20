"""Comfy finishing orchestrator — Phase 18.

PoseBundle frame → OpenPose control image → ComfyUI (checkpoint + openpose ControlNet)
→ stylized frame. The 3D pose drives generation via the ControlNet, so the requested
pose is preserved.
"""

from __future__ import annotations

import json
from pathlib import Path

from comfy.comfy_client import ComfyClient, build_workflow
from comfy.openpose_draw import draw_openpose
from comfy.style_profile import StyleProfile


def finish_frame(client: ComfyClient, sp: StyleProfile, frame_dir: str,
                 out_dir: str, *, seed: int = 42) -> dict:
    frame_dir = Path(frame_dir)
    pose = json.loads((frame_dir / "pose.json").read_text())

    openpose_path = str(frame_dir / "openpose.png")
    draw_openpose(pose["actors"], (sp.width, sp.height), openpose_path)

    uploaded = client.upload_image(openpose_path)
    workflow = build_workflow(sp, uploaded, seed=seed)
    prompt_id = client.queue(workflow)
    history = client.wait(prompt_id)
    outputs = client.download_outputs(history, out_dir)
    if not outputs:
        raise RuntimeError("Comfy produced no output image")
    return {"stylized": outputs[0], "openpose": openpose_path, "prompt_id": prompt_id}
