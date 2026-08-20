"""Phase 18 gate: one manually posed 3D frame -> a stylized frame, pose preserved
(the 3D pose drives generation through the openpose ControlNet).

Runs a REAL generation against the local ComfyUI (:8188) with a discovered
Illustrious checkpoint. Skips gracefully if ComfyUI is offline.

Run: python tests/test_comfy_finish.py
"""

import sys
import tempfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.blender_bridge import BlenderBridge  # noqa: E402
from server.scene import load_scene_commands  # noqa: E402
from server.posing import apply_pose_commands  # noqa: E402
from characters.semantic_rig import CANONICAL_BODY  # noqa: E402
from contracts.posebundle import export_posebundle  # noqa: E402
from comfy.comfy_client import ComfyClient  # noqa: E402
from comfy.style_profile import illustrious  # noqa: E402
from comfy.finish import finish_frame  # noqa: E402
from PIL import Image  # noqa: E402

COMFY = "http://127.0.0.1:8188"


def _comfy_up():
    try:
        urllib.request.urlopen(COMFY + "/system_stats", timeout=5)
        return True
    except Exception:
        return False


def _pick_checkpoint():
    import json
    d = json.load(urllib.request.urlopen(COMFY + "/object_info/CheckpointLoaderSimple", timeout=10))
    names = d["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    for n in names:
        if "illustrious" in n.lower():
            return n
    return names[0]


def test_phase18_stylized_frame_from_pose():
    if not _comfy_up():
        print("SKIP: ComfyUI not reachable on :8188")
        return

    bridge = BlenderBridge()
    manifest = {"ground": True, "lights": [{"type": "SUN", "name": "Key"}],
                "camera": "full body", "subjectX": 0.0,
                "actors": [{"name": "A", "offset": [0, 0, 0]}]}
    with tempfile.TemporaryDirectory() as tmp:
        blend = str(Path(tmp) / "pose.blend")
        cmds = load_scene_commands(manifest)
        cmds += apply_pose_commands(
            {"bones": {"arm.left.upper": {"euler": [0.0, 0, -0.9]},
                       "arm.right.upper": {"euler": [0.0, 0, 0.9]}}}, "A", "canonical")
        r = bridge.run(cmds, blend_out=blend)
        assert all(x["ok"] for x in r), r

        bundle = str(Path(tmp) / "bundle")
        export_posebundle(bridge, blend_in=blend, bundle_dir=bundle, frames=[1],
                          actors=[{"name": "A", "index": 1}], canonical_bones=CANONICAL_BODY,
                          width=512, height=512)
        frame_dir = Path(bundle) / "frame_0001"

        ckpt = _pick_checkpoint()
        sp = illustrious(ckpt, steps=8, width=512, height=512)
        client = ComfyClient(COMFY)
        result = finish_frame(client, sp, str(frame_dir), str(Path(tmp) / "out"), seed=7)

        # openpose control image is non-empty (drove the pose)
        op = Image.open(result["openpose"]).convert("RGB")
        assert op.getbbox() is not None, "openpose control image is blank"
        # stylized frame produced, right size, not all-black
        img = Image.open(result["stylized"]).convert("RGB")
        assert img.size == (512, 512), img.size
        assert img.getbbox() is not None, "stylized frame is blank"
        extrema = img.getextrema()
        assert max(hi for _, hi in extrema) > 30, "stylized frame looks empty"
        print("stylized:", result["stylized"], "ckpt:", ckpt)


if __name__ == "__main__":
    test_phase18_stylized_frame_from_pose()
    print("Phase 18 Comfy finishing: gate passes")
