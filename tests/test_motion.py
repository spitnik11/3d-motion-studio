"""Phase 12 gate: import a motion and manually alter hand/arm/foot/timing after
retargeting. Real headless Blender. We author a motion on actor SRC, export BVH,
import it, retarget onto actor DST, then edit DST and confirm edits + motion coexist.

Run: python tests/test_motion.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.blender_bridge import BlenderBridge  # noqa: E402
from server.registry.registry import AssetRegistry  # noqa: E402
from server.posing import apply_pose_commands  # noqa: E402
from server.motion import retarget_commands, register_motion  # noqa: E402

FAM = "canonical"


def test_phase12_import_retarget_then_edit():
    bridge = BlenderBridge()
    frames = [1, 4, 8]
    with tempfile.TemporaryDirectory() as tmp:
        bvh = str(Path(tmp) / "walk.bvh")
        # Author motion on SRC and export BVH.
        cmds = [{"op": "newScene"}, {"op": "createHumanoidFixture", "name": "SRC"}]
        for i, f in enumerate(frames):
            t = i / (len(frames) - 1)
            cmds += apply_pose_commands({"bones": {"arm.left.upper": {"euler": [t * 1.2, 0, 0]}}},
                                        "SRC", FAM, frame=f, keyframe=True)
        cmds += [{"op": "setFrame", "frame": 1},
                 {"op": "exportBVH", "armature": "SRC", "path": bvh, "frame_start": 1, "frame_end": 8}]
        r = bridge.run(cmds)
        assert all(x["ok"] for x in r), r

        reg = AssetRegistry(":memory:")
        rec = register_motion(reg, "walk", bvh, source="self-test", frames=8)
        assert rec["kind"] == "MotionAsset" and rec["format"] == "bvh"

        # Import BVH (own armature), retarget onto DST, then manually edit DST.
        blend = str(Path(tmp) / "out.blend")
        r2 = bridge.run(
            [
                {"op": "newScene"},
                {"op": "createHumanoidFixture", "name": "DST"},
                {"op": "importModel", "path": bvh},  # imports a BVH armature w/ action
            ]
            + retarget_commands(_bvh_arm_name(bvh), "DST", frames=[1, 4, 8])
            # manual edit AFTER retarget: override DST hand at frame 8, keep the rest
            + apply_pose_commands({"bones": {"hand.right": {"euler": [0.5, 0, 0]}}},
                                  "DST", FAM, frame=8, keyframe=True),
            blend_out=blend,
        )
        for x in r2:
            assert x["ok"], x
        retarget_res = next(x for x in r2 if x["op"] == "retargetMotion")
        assert retarget_res["keys"] > 0, retarget_res

        # Verify: retargeted arm animates over time AND the manual hand edit stuck.
        chk = bridge.run([
            {"op": "setFrame", "frame": 1},
            {"op": "getBoneRotation", "armature": "DST", "bone": "arm.left.upper"},
            {"op": "setFrame", "frame": 8},
            {"op": "getBoneRotation", "armature": "DST", "bone": "arm.left.upper"},
            {"op": "getBoneRotation", "armature": "DST", "bone": "hand.right"},
        ], blend_in=blend)
        assert all(x["ok"] for x in chk), chk
        arm_f1, arm_f8 = chk[1]["euler"][0], chk[3]["euler"][0]
        assert arm_f8 - arm_f1 > 0.8, f"retargeted motion not driving: {arm_f1}->{arm_f8}"
        assert abs(chk[4]["euler"][0] - 0.5) < 1e-3, "manual edit after retarget lost"


def _bvh_arm_name(bvh_path):
    # Blender names the imported BVH armature after the file stem.
    return Path(bvh_path).stem


if __name__ == "__main__":
    test_phase12_import_retarget_then_edit()
    print("Phase 12 motion import + retarget: gate passes")
