"""Phase 5 gate: one semantic command resolves across 3 rig families, and applies
live on a real armature (the generated canonical fixture).

Run: python tests/test_semantic_rig.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from characters.semantic_rig import SemanticRig, detect_family, CANONICAL  # noqa: E402
from server.blender_bridge import BlenderBridge  # noqa: E402


def test_semantic_command_resolves_across_families():
    cmd = "arm.left.upper"
    assert SemanticRig("mixamo").family_bone(cmd) == "mixamorig:LeftArm"
    assert SemanticRig("vrm").family_bone(cmd) == "leftUpperArm"
    assert SemanticRig("quaternius").family_bone(cmd) == "UpperArm_L"
    assert SemanticRig("rigify").family_bone(cmd) == "upper_arm.L"
    # finger command resolves too
    assert SemanticRig("mixamo").family_bone("hand.right.index.2") == "mixamorig:RightHandIndex2"


def test_all_canonical_mapped_in_each_family():
    for fam in ("vrm", "rigify", "quaternius", "mixamo", "mpfb", "canonical"):
        assert SemanticRig(fam).unmapped() == [], f"{fam} has unmapped canonical bones"


def test_live_semantic_command_on_fixture():
    bridge = BlenderBridge()
    rig = SemanticRig("canonical")
    bone = rig.family_bone("arm.left.upper")  # identity → "arm.left.upper"

    with tempfile.TemporaryDirectory() as tmp:
        blend = str(Path(tmp) / "actor.blend")
        r1 = bridge.run(
            [
                {"op": "newScene"},
                {"op": "createHumanoidFixture", "name": "ActorA"},
                {"op": "setBoneRotation", "armature": "ActorA", "bone": bone, "euler": [0.6, 0, 0]},
            ],
            blend_out=blend,
        )
        assert all(r["ok"] for r in r1), r1
        assert r1[1]["bones"] > 40, r1[1]  # body + fingers

        r2 = bridge.run(
            [{"op": "getBoneRotation", "armature": "ActorA", "bone": bone}],
            blend_in=blend,
        )
        assert r2[0]["ok"], r2
        assert abs(r2[0]["euler"][0] - 0.6) < 1e-4, r2[0]


def test_detect_family_on_fixture_bones():
    # Canonical fixture bone names → detected as 'canonical'.
    assert detect_family(CANONICAL) == "canonical"
    # A mixamo-looking set → 'mixamo'.
    mixamo_names = [SemanticRig("mixamo").family_bone(c) for c in CANONICAL]
    assert detect_family(mixamo_names) == "mixamo"


if __name__ == "__main__":
    test_semantic_command_resolves_across_families()
    test_all_canonical_mapped_in_each_family()
    test_live_semantic_command_on_fixture()
    test_detect_family_on_fixture_bones()
    print("Phase 5 SemanticRig: gate passes")
