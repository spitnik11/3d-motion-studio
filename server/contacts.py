"""Contacts & pair poses — Phases 9-10.

A ContactConstraint pins one actor's joint to a region on another actor. It is
model-agnostic (canonical joint names) and realized in Blender as a Copy Location
constraint (the lazy-but-real contact primitive; IK/Child-Of variants can be added
per type later).

A PairPose bundles two actor poses + their relative transform + contacts + locks +
camera, with NO model names baked in — so it re-applies to any compatible pair.
"""

from __future__ import annotations

from characters.semantic_rig import SemanticRig
from server.posing import apply_pose_commands


def contact(source_joint: str, target_region: str, *, type: str = "position",
            strength: float = 1.0) -> dict:
    """One ContactConstraint (actors are supplied at apply time, not baked in)."""
    return {
        "sourceJoint": source_joint,
        "targetRegion": target_region,
        "type": type,
        "strength": strength,
    }


def apply_contacts_commands(contacts, *, source_armature: str, source_family: str,
                            target_armature: str, target_family: str) -> list[dict]:
    src_rig = SemanticRig(source_family)
    tgt_rig = SemanticRig(target_family)
    cmds = []
    for i, c in enumerate(contacts):
        cmds.append({
            "op": "addCopyLocationConstraint",
            "armature": source_armature,
            "bone": src_rig.family_bone(c["sourceJoint"]),
            "targetArmature": target_armature,
            "targetBone": tgt_rig.family_bone(c["targetRegion"]),
            "influence": c.get("strength", 1.0),
            "name": f"contact_{i}_{c['sourceJoint']}",
        })
    return cmds


def pair_pose(pose_a, pose_b, *, relative_transform=None, contacts=None,
              locks=None, camera=None, category: str = "custom", meta=None) -> dict:
    """Build a PairPoseAsset payload. relative_transform = B's object-space offset from A."""
    return {
        "actorA": {"pose": pose_a},
        "actorB": {"pose": pose_b},
        "relativeTransform": relative_transform or {"location": [0.6, 0.0, 0.0]},
        "contacts": contacts or [],
        "locks": sorted(locks or []),
        "camera": camera,
        "category": category,
        "meta": meta or {},
    }


def apply_pairpose_commands(pp, *, armature_a: str, family_a: str,
                            armature_b: str, family_b: str,
                            locks: set[str] | None = None) -> list[dict]:
    """Commands to realize a PairPose on a concrete (possibly different) pair."""
    cmds = [{"op": "newScene"}]
    cmds.append({"op": "createHumanoidFixture", "name": armature_a})
    b_off = pp["relativeTransform"].get("location", [0.6, 0, 0])
    cmds.append({"op": "createHumanoidFixture", "name": armature_b, "offset": b_off})
    cmds += apply_pose_commands(pp["actorA"]["pose"], armature_a, family_a, locks=locks)
    cmds += apply_pose_commands(pp["actorB"]["pose"], armature_b, family_b, locks=locks)
    cmds += apply_contacts_commands(
        pp["contacts"],
        source_armature=armature_a, source_family=family_a,
        target_armature=armature_b, target_family=family_b,
    )
    return cmds
