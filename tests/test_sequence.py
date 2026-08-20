"""Phase 19 gate (MVP star): reject one frame, regenerate ONLY that frame, and leave
the neighbors byte-for-byte untouched. Real generations against local ComfyUI.

Run: python tests/test_sequence.py
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
from comfy.sequence import finish_sequence, set_status, rejected_frames, regenerate_frames  # noqa: E402

COMFY = "http://127.0.0.1:8188"


def _comfy_up():
    try:
        urllib.request.urlopen(COMFY + "/system_stats", timeout=5)
        return True
    except Exception:
        return False


def _ckpt():
    import json
    d = json.load(urllib.request.urlopen(COMFY + "/object_info/CheckpointLoaderSimple", timeout=10))
    names = d["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    return next((n for n in names if "illustrious" in n.lower()), names[0])


def test_phase19_selective_regen():
    if not _comfy_up():
        print("SKIP: ComfyUI not reachable on :8188")
        return

    bridge = BlenderBridge()
    frames = [1, 2, 3]
    manifest = {"ground": True, "lights": [{"type": "SUN", "name": "Key"}],
                "camera": "full body", "subjectX": 0.0,
                "actors": [{"name": "A", "offset": [0, 0, 0]}]}
    with tempfile.TemporaryDirectory() as tmp:
        blend = str(Path(tmp) / "anim.blend")
        cmds = load_scene_commands(manifest)
        for i, f in enumerate(frames):
            t = i / (len(frames) - 1)
            cmds += apply_pose_commands(
                {"bones": {"arm.left.upper": {"euler": [0, 0, -0.3 - t]}}}, "A", "canonical",
                frame=f, keyframe=True)
        assert all(x["ok"] for x in bridge.run(cmds, blend_out=blend))

        bundle = str(Path(tmp) / "bundle")
        export_posebundle(bridge, blend_in=blend, bundle_dir=bundle, frames=frames,
                          actors=[{"name": "A", "index": 1}], canonical_bones=CANONICAL_BODY,
                          width=384, height=384)

        out = str(Path(tmp) / "out")
        sp = illustrious(_ckpt(), steps=6, width=384, height=384)
        client = ComfyClient(COMFY)
        finish_sequence(client, sp, bundle, out, seed=100)

        before = {f: (Path(out) / f"frame_{f:04d}.png").read_bytes() for f in frames}

        # Reject frame 2, regenerate only rejected frames.
        set_status(out, 2, "rejected")
        assert rejected_frames(out) == [2]
        regenerate_frames(client, sp, bundle, out, rejected_frames(out))

        after = {f: (Path(out) / f"frame_{f:04d}.png").read_bytes() for f in frames}
        assert after[2] != before[2], "rejected frame 2 was not regenerated"
        assert after[1] == before[1], "frame 1 changed but should be untouched"
        assert after[3] == before[3], "frame 3 changed but should be untouched"
        print("selective regen OK: only frame 2 changed")


if __name__ == "__main__":
    test_phase19_selective_regen()
    print("Phase 19 full sequence + selective regen: gate passes")
