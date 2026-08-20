"""Gates for the manual-posing core — Phases 6-11. Real headless Blender.

  6  create + recall 5 poses (no AI)
  7  a hand pose transfers via SemanticRig to two characters
  8  automation cannot move a locked bone
  9  three paired contact constraints save & hold
 10  a PairPose re-applies to a different compatible pair
 11  an 8-frame paired animation, keyframed, no AI

Run: python tests/test_manual_posing.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.blender_bridge import BlenderBridge  # noqa: E402
from server.registry.registry import AssetRegistry  # noqa: E402
from server.posing import (  # noqa: E402
    apply_pose_commands, mirror_pose, hand_pose, canonical_finger,
)
from server.contacts import contact, pair_pose, apply_pairpose_commands  # noqa: E402

FAM = "canonical"


def _two_actors_cmds(b_off=(0.6, 0, 0)):
    return [
        {"op": "newScene"},
        {"op": "createHumanoidFixture", "name": "A"},
        {"op": "createHumanoidFixture", "name": "B", "offset": list(b_off)},
    ]


def test_phase6_create_and_recall_five_poses():
    bridge = BlenderBridge()
    reg = AssetRegistry(":memory:")
    poses = {
        "wave":   {"bones": {"arm.left.upper": {"euler": [0.9, 0, 0]}}, "meta": {}},
        "reach":  {"bones": {"arm.right.upper": {"euler": [-0.8, 0, 0]}}, "meta": {}},
        "bow":    {"bones": {"spine.lower": {"euler": [0.5, 0, 0]}}, "meta": {}},
        "kick":   {"bones": {"leg.right.upper": {"euler": [-1.0, 0, 0]}}, "meta": {}},
        "shrug":  {"bones": {"shoulder.left": {"euler": [0, 0, 0.4]}}, "meta": {}},
    }
    ids = {name: reg.register("PoseAsset", name, payload=p)["id"] for name, p in poses.items()}

    # Recall each: reload from registry, apply, read back the driven bone.
    for name, aid in ids.items():
        p = reg.get(aid)["payload"]
        (canonical, spec), = p["bones"].items()
        with tempfile.TemporaryDirectory() as tmp:
            blend = str(Path(tmp) / "p.blend")
            r = bridge.run(
                [{"op": "newScene"}, {"op": "createHumanoidFixture", "name": "A"}]
                + apply_pose_commands(p, "A", FAM),
                blend_out=blend,
            )
            assert all(x["ok"] for x in r), (name, r)
            rr = bridge.run(read_one(canonical, "A"), blend_in=blend)
            assert rr[0]["ok"] and _close(rr[0]["euler"], spec["euler"]), (name, rr)


def read_one(canonical, arm):
    from characters.semantic_rig import SemanticRig
    return [{"op": "getBoneRotation", "armature": arm, "bone": SemanticRig(FAM).family_bone(canonical)}]


def test_mirror_pose_is_involutive():
    p = {"bones": {"arm.left.upper": {"euler": [0.2, 0.3, 0.4], "location": [0.1, 0, 0]}}, "meta": {}}
    back = mirror_pose(mirror_pose(p))
    assert _close(back["bones"]["arm.left.upper"]["euler"], [0.2, 0.3, 0.4])
    assert "arm.right.upper" in mirror_pose(p)["bones"]


def test_phase7_handpose_transfers_to_two_characters():
    bridge = BlenderBridge()
    fist = hand_pose("fist", side="left")
    tip = canonical_finger("left", "index", 3)
    cmds = _two_actors_cmds()
    cmds += apply_pose_commands(fist, "A", FAM)
    cmds += apply_pose_commands(fist, "B", FAM)
    r = bridge.run(
        cmds + [
            {"op": "getBoneRotation", "armature": "A", "bone": tip},
            {"op": "getBoneRotation", "armature": "B", "bone": tip},
        ]
    )
    assert all(x["ok"] for x in r), r
    assert r[-2]["euler"][0] > 1.0 and r[-1]["euler"][0] > 1.0, "fist not applied to both"


def test_phase8_locked_bone_is_never_moved():
    bridge = BlenderBridge()
    locks = {"hand.right"}
    pose = {"bones": {"hand.right": {"euler": [1.0, 0, 0]},
                      "arm.left.upper": {"euler": [0.5, 0, 0]}}, "meta": {}}
    cmds = [{"op": "newScene"}, {"op": "createHumanoidFixture", "name": "A"}]
    cmds += apply_pose_commands(pose, "A", FAM, locks=locks)
    r = bridge.run(cmds + [
        {"op": "getBoneRotation", "armature": "A", "bone": "hand.right"},
        {"op": "getBoneRotation", "armature": "A", "bone": "arm.left.upper"},
    ])
    assert all(x["ok"] for x in r), r
    assert _close(r[-2]["euler"], [0, 0, 0]), "locked bone was moved!"
    assert _close(r[-1]["euler"], [0.5, 0, 0]), "unlocked bone not moved"


def test_phase9_three_contacts_save_and_hold():
    bridge = BlenderBridge()
    contacts = [
        contact("hand.right", "arm.left.lower"),
        contact("hand.left", "spine.upper"),
        contact("foot.left", "foot.right"),
    ]
    from server.contacts import apply_contacts_commands
    cmds = _two_actors_cmds()
    cmds += apply_contacts_commands(
        contacts, source_armature="A", source_family=FAM,
        target_armature="B", target_family=FAM)
    with tempfile.TemporaryDirectory() as tmp:
        blend = str(Path(tmp) / "pair.blend")
        r = bridge.run(cmds, blend_out=blend)
        assert all(x["ok"] for x in r), r
        # Reopen → constraints persisted + source pinned to target.
        chk = bridge.run([
            {"op": "listConstraints", "armature": "A", "bone": "hand.right"},
            {"op": "getBoneWorldHead", "armature": "A", "bone": "hand.right"},
            {"op": "getBoneWorldHead", "armature": "B", "bone": "arm.left.lower"},
        ], blend_in=blend)
        assert chk[0]["constraints"] and chk[0]["constraints"][0]["type"] == "COPY_LOCATION"
        d = _dist(chk[1]["world"], chk[2]["world"])
        assert d < 0.05, f"contact did not hold: dist={d}"


def test_phase10_pairpose_reapplies_to_different_pair():
    bridge = BlenderBridge()
    pp = pair_pose(
        pose_a={"bones": {"arm.right.upper": {"euler": [-0.7, 0, 0]}}, "meta": {}},
        pose_b={"bones": {"arm.left.upper": {"euler": [0.7, 0, 0]}}, "meta": {}},
        relative_transform={"location": [0.7, 0, 0]},
        contacts=[contact("hand.right", "arm.left.lower")],
        category="support",
    )
    # Apply to a DIFFERENT pair (C/D) — no model names baked in.
    cmds = apply_pairpose_commands(pp, armature_a="C", family_a=FAM,
                                   armature_b="D", family_b=FAM)
    r = bridge.run(cmds + [
        {"op": "listConstraints", "armature": "C", "bone": "hand.right"},
        {"op": "getBoneRotation", "armature": "C", "bone": "arm.right.upper"},
    ])
    assert all(x["ok"] for x in r), r
    assert r[-2]["constraints"], "pair contact not applied to new pair"
    assert _close(r[-1]["euler"], [-0.7, 0, 0]), "pair pose A not applied"


def test_phase11_eight_frame_paired_animation():
    bridge = BlenderBridge()
    cmds = _two_actors_cmds()
    # Keyframe both actors across 8 frames: left arm swings up over time.
    for i, frame in enumerate(range(1, 9)):
        t = i / 7.0
        pa = {"bones": {"arm.left.upper": {"euler": [t * 1.2, 0, 0]}}, "meta": {}}
        pb = {"bones": {"arm.right.upper": {"euler": [-t * 1.2, 0, 0]}}, "meta": {}}
        cmds += apply_pose_commands(pa, "A", FAM, frame=frame, keyframe=True)
        cmds += apply_pose_commands(pb, "B", FAM, frame=frame, keyframe=True)
    with tempfile.TemporaryDirectory() as tmp:
        blend = str(Path(tmp) / "anim.blend")
        r = bridge.run(cmds, blend_out=blend)
        assert all(x["ok"] for x in r), r
        chk = bridge.run([
            {"op": "countKeyframes", "armature": "A"},
            {"op": "setFrame", "frame": 1},
            {"op": "getBoneRotation", "armature": "A", "bone": "arm.left.upper"},
            {"op": "setFrame", "frame": 8},
            {"op": "getBoneRotation", "armature": "A", "bone": "arm.left.upper"},
        ], blend_in=blend)
        assert chk[0]["keyframes"] >= 8, chk[0]
        f1, f8 = chk[2]["euler"][0], chk[4]["euler"][0]
        assert f8 - f1 > 0.9, f"animation not driving over time: {f1}->{f8}"


# ---- helpers ---------------------------------------------------------------
def _close(a, b, eps=1e-3):
    return all(abs(x - y) < eps for x, y in zip(a, b))


def _dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


if __name__ == "__main__":
    test_mirror_pose_is_involutive()
    test_phase6_create_and_recall_five_poses()
    test_phase7_handpose_transfers_to_two_characters()
    test_phase8_locked_bone_is_never_moved()
    test_phase9_three_contacts_save_and_hold()
    test_phase10_pairpose_reapplies_to_different_pair()
    test_phase11_eight_frame_paired_animation()
    print("Phases 6-11 manual posing: gates pass")
