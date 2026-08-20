"""Close the AI loop for CHARACTERS (Phase 22 made real):
generated humanoid mesh (SPAR3D) → UniRig skeleton → auto-calibrate to SemanticRig →
pose it with a semantic command. Proves a generated+rigged character is poseable.

Uses Z:/ai-assets/humanoid/skeleton.fbx (produced by SPAR3D→UniRig). Skips if absent.

Run: python tests/test_generated_character.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.blender_bridge import BlenderBridge  # noqa: E402
from server.registry.registry import AssetRegistry  # noqa: E402
from server.posing import apply_pose_commands  # noqa: E402
from characters.calibrate import calibrate_skeleton  # noqa: E402

SKELETON = "Z:/ai-assets/humanoid/skeleton.fbx"


def test_generated_humanoid_calibrate_and_pose():
    if not Path(SKELETON).is_file():
        print("SKIP: no generated humanoid skeleton (run SPAR3D→UniRig first)")
        return
    bridge = BlenderBridge()
    arm = bridge.run([{"op": "newScene"}, {"op": "importModel", "path": SKELETON},
                      {"op": "listArmatures"}])[2]["armatures"][0]

    graph = bridge.run([{"op": "importModel", "path": SKELETON},
                        {"op": "armatureGraph", "armature": arm}])[1]["bones"]
    cal = calibrate_skeleton(graph)
    assert cal["coverage"] >= 0.5, f"calibration coverage too low: {cal['coverage']}"
    mapping = cal["mapping"]

    # Register the generated+rigged character with its calibration.
    reg = AssetRegistry(":memory:")
    rec = reg.register("CharacterAsset", "GeneratedHumanoid", source="SPAR3D+UniRig",
                       localPath=SKELETON, format="fbx",
                       payload={"generated": True, "calibration": mapping,
                                "coverage": cal["coverage"], "armature": arm})
    assert rec["payload"]["calibration"]

    # A semantic command poses the generated character via the calibrated map.
    target = "arm.left.upper" if "arm.left.upper" in mapping else next(
        k for k in ("spine.lower", "leg.left.upper", "head") if k in mapping)
    blend = str(Path(rec["payload"].get("blend", "")) or "")  # not saved; pose in-session
    with __import__("tempfile").TemporaryDirectory() as tmp:
        b = str(Path(tmp) / "c.blend")
        cmds = [{"op": "newScene"}, {"op": "importModel", "path": SKELETON}]
        cmds += apply_pose_commands({"bones": {target: {"euler": [0.6, 0, 0]}}},
                                    arm, "custom", mapping=mapping)
        assert all(x["ok"] for x in bridge.run(cmds, blend_out=b)), "pose apply failed"
        rr = bridge.run([{"op": "getBoneRotation", "armature": arm, "bone": mapping[target]}],
                        blend_in=b)
        assert rr[0]["ok"] and abs(rr[0]["euler"][0] - 0.6) < 1e-3, "semantic pose didn't drive bone"
    print(f"generated humanoid posed via calibrated '{target}' -> {mapping[target]} "
          f"(coverage {cal['coverage']:.0%})")


if __name__ == "__main__":
    test_generated_humanoid_calibrate_and_pose()
    print("Generated-character loop: gate passes")
