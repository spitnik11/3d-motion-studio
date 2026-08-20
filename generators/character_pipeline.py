"""Generated humanoid pipeline — Phase 22.

reference → mesh → topology check → cleanup → rig → weights → deformation QA →
SemanticRig mapping → approval. Generated people are NEVER auto-promoted to Hero
Characters; they must pass deformation QA first. The AI stages are gated providers;
deformation QA itself is real and runs on any rigged character.
"""

from __future__ import annotations

from server.blender_bridge import BlenderBridge

# Joints exercised by deformation QA (plan Phase 22).
QA_JOINTS = ["shoulder.left", "arm.left.lower", "hand.left",
             "leg.left.upper", "leg.left.lower", "foot.left", "spine.lower"]


def deformation_qa(blend_in: str, armature: str, mesh: str, *,
                   bridge: BlenderBridge | None = None, angle: float = 0.6) -> dict:
    """Pose each test joint and confirm the mesh deforms finitely (no explosion, no NaN).

    Returns {"passed": bool, "joints": {joint: {moved, finite}}}.
    """
    bridge = bridge or BlenderBridge()
    rest = bridge.run([{"op": "evaluatedMeshBounds", "mesh": mesh}], blend_in=blend_in)[0]
    rest_box = (rest["min"], rest["max"])

    joints = {}
    for j in QA_JOINTS:
        r = bridge.run([
            {"op": "setBoneRotation", "armature": armature, "bone": j, "euler": [angle, 0, 0]},
            {"op": "evaluatedMeshBounds", "mesh": mesh},
            {"op": "setBoneRotation", "armature": armature, "bone": j, "euler": [0, 0, 0]},
        ], blend_in=blend_in)
        box = r[1]
        moved = box["min"] != rest_box[0] or box["max"] != rest_box[1]
        joints[j] = {"moved": moved, "finite": box.get("finite", False)}

    passed = all(v["finite"] for v in joints.values()) and any(v["moved"] for v in joints.values())
    return {"passed": passed, "joints": joints}
