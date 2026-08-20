"""Real-asset gate (Phase 4/5 with genuine downloads):
a real CC0 VRoid VRM + a Khronos rigged GLB load, the family is detected, and a
semantic command drives the ACTUAL character bones.

Assets (CC0 / CC-BY), downloaded to Z:/ai-assets/characters:
  AvatarSample_B.vrm  (VRoid CC0)   · CesiumMan.glb (Khronos CC-BY)

Run: python tests/test_real_assets.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.blender_bridge import BlenderBridge  # noqa: E402
from server.registry.registry import AssetRegistry  # noqa: E402
from server.character_import import CharacterImporter  # noqa: E402
from characters.semantic_rig import SemanticRig, detect_family  # noqa: E402

VRM = "Z:/ai-assets/characters/AvatarSample_B.vrm"
GLB = "Z:/ai-assets/characters/CesiumMan.glb"


def test_vroid_vrm_import_and_semantic_pose():
    if not Path(VRM).is_file():
        print("SKIP: VRM asset not present")
        return
    bridge = BlenderBridge()
    registry = AssetRegistry(":memory:")

    rec = CharacterImporter(bridge=bridge, registry=registry).import_character(
        VRM, name="AvatarSample_B", source="VRoid sample (CC0)",
        license="CC0", creator="VRoid Project")
    assert rec["kind"] == "CharacterAsset"
    assert rec["payload"]["armatures"], "no armature"
    assert rec["payload"]["materials"], "no materials"
    assert rec["sha256"], "no provenance hash"

    arm = rec["payload"]["armatures"][0]
    blend = rec["payload"]["blend"]
    bones = bridge.run([{"op": "listBones", "armature": arm}], blend_in=blend)[0]["bones"]
    fam = detect_family(bones)
    assert fam == "vroid", f"expected vroid family, detected {fam}"

    # A semantic command drives the REAL character's bones.
    rig = SemanticRig("vroid")
    for canonical in ("arm.left.upper", "hand.right", "leg.left.lower", "head",
                      "hand.left.index.2"):
        b = rig.family_bone(canonical)
        assert b in bones, f"vroid mapping bone {b!r} ({canonical}) not on real rig"

    r = bridge.run([
        {"op": "setBoneRotation", "armature": arm, "bone": rig.family_bone("arm.left.upper"),
         "euler": [0.5, 0, 0]},
        {"op": "getBoneRotation", "armature": arm, "bone": rig.family_bone("arm.left.upper")},
    ], blend_in=blend)
    assert r[0]["ok"] and abs(r[1]["euler"][0] - 0.5) < 1e-3, "semantic pose failed on real VRM"


def test_khronos_glb_import():
    if not Path(GLB).is_file():
        print("SKIP: GLB asset not present")
        return
    bridge = BlenderBridge()
    registry = AssetRegistry(":memory:")
    rec = CharacterImporter(bridge=bridge, registry=registry).import_character(
        GLB, name="CesiumMan", source="Khronos glTF-Sample-Assets", license="CC-BY 4.0")
    assert rec["payload"]["armatures"], "no armature in CesiumMan"
    assert rec["sha256"]


if __name__ == "__main__":
    test_vroid_vrm_import_and_semantic_pose()
    test_khronos_glb_import()
    print("Real-asset import + semantic pose: gates pass")
