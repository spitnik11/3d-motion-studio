"""Posing engine — Phases 6-11.

A Pose is model-agnostic: {canonical_bone: {"euler": [x,y,z], "location": [x,y,z]?}}.
Applying it resolves each canonical bone to the target rig's family name and drives
the bone through the BlenderBridge. The same engine powers:

- Phase 6  body poses (save/load/mirror/reset)
- Phase 7  hand poses (poses over finger bones; the preset library below)
- Phase 8  pose locks (locked canonical bones are never driven by automation)
- Phase 11 manual animation (poses keyframed at frames)

Pair poses / contacts (Phases 9-10) live in contacts.py and build on this.
"""

from __future__ import annotations

from characters.semantic_rig import (
    SIDES, FINGERS, FINGER_SEGS, canonical_finger, SemanticRig,
)

Pose = dict  # {"bones": {canonical: {"euler":[...], "location":[...]?}}, "meta": {...}}


def apply_pose_commands(pose: Pose, armature: str, family: str,
                        *, frame: int | None = None, keyframe: bool = False,
                        locks: set[str] | None = None, mapping: dict | None = None) -> list[dict]:
    """Bridge command list that applies `pose` to `armature`.

    Locked canonical bones are skipped entirely — automation cannot move them.
    Pass `mapping` (from calibrate_skeleton) to drive a calibrated generated rig.
    """
    rig = SemanticRig(family, mapping=mapping)
    locks = locks or set()
    cmds: list[dict] = []
    if frame is not None:
        cmds.append({"op": "setFrame", "frame": frame})
    for canonical, spec in pose.get("bones", {}).items():
        if canonical in locks:
            continue
        bone = rig.family_bone(canonical)
        if bone is None:
            continue  # unmapped → calibration handles it
        if "euler" in spec:
            cmds.append({"op": "setBoneRotation", "armature": armature, "bone": bone,
                         "euler": spec["euler"]})
        if "location" in spec:
            cmds.append({"op": "setBoneLocation", "armature": armature, "bone": bone,
                         "location": spec["location"]})
        if keyframe:
            paths = ["rotation_euler"] + (["location"] if "location" in spec else [])
            cmds.append({"op": "insertKeyframe", "armature": armature, "bone": bone,
                         "frame": frame, "paths": paths})
    return cmds


def read_pose_commands(canonical_bones, armature: str, family: str) -> list[dict]:
    rig = SemanticRig(family)
    return [
        {"op": "getBoneRotation", "armature": armature, "bone": rig.family_bone(c)}
        for c in canonical_bones if rig.family_bone(c)
    ]


def mirror_pose(pose: Pose) -> Pose:
    """Mirror across the X plane: swap .left/.right and flip Y,Z rotation + X location."""
    def swap_side(name: str) -> str:
        if ".left" in name:
            return name.replace(".left", ".right")
        if ".right" in name:
            return name.replace(".right", ".left")
        return name

    out = {"bones": {}, "meta": {**pose.get("meta", {}), "mirrored": True}}
    for canonical, spec in pose.get("bones", {}).items():
        m = {}
        if "euler" in spec:
            x, y, z = spec["euler"]
            m["euler"] = [x, -y, -z]
        if "location" in spec:
            lx, ly, lz = spec["location"]
            m["location"] = [-lx, ly, lz]
        out["bones"][swap_side(canonical)] = m
    return out


# ---- hand pose preset library (Phase 7) ------------------------------------
# Curl = rotation about local X on each finger segment (radians). Positive = flexion.

def _hand(side: str, curl: float, thumb_curl: float | None = None, spread: float = 0.0) -> dict:
    bones = {}
    for fi, finger in enumerate(FINGERS):
        c = thumb_curl if (finger == "thumb" and thumb_curl is not None) else curl
        for n in FINGER_SEGS:
            sp = spread * (fi - 2) if n == 1 else 0.0
            bones[canonical_finger(side, finger, n)] = {"euler": [c, 0.0, sp]}
    return bones


def hand_pose(name: str, side: str = "left") -> Pose:
    presets = {
        "relaxed":   dict(curl=0.35, thumb_curl=0.25, spread=0.05),
        "open":      dict(curl=0.0, thumb_curl=0.0, spread=0.12),
        "flat-palm": dict(curl=0.0, thumb_curl=0.0, spread=0.0),
        "fist":      dict(curl=1.45, thumb_curl=1.0, spread=0.0),
        "half-fist": dict(curl=0.8, thumb_curl=0.6, spread=0.0),
        "point":     dict(curl=1.45, thumb_curl=0.8, spread=0.0),
        "pinch":     dict(curl=0.9, thumb_curl=0.9, spread=0.0),
        "wrist-grip": dict(curl=1.2, thumb_curl=1.0, spread=0.0),
        "support-grip": dict(curl=1.0, thumb_curl=0.9, spread=0.0),
    }
    if name not in presets:
        raise ValueError(f"unknown hand pose {name!r}; have {sorted(presets)}")
    p = presets[name]
    # point = index extended
    bones = _hand(side, **p)
    if name == "point":
        for n in FINGER_SEGS:
            bones[canonical_finger(side, "index", n)] = {"euler": [0.0, 0.0, 0.0]}
    return {"bones": bones, "meta": {"kind": "hand", "preset": name, "side": side}}


# A couple of ready body poses for tests / defaults.
def tpose() -> Pose:
    return {"bones": {}, "meta": {"name": "tpose"}}


def arms_down() -> Pose:
    b = {}
    b["arm.left.upper"] = {"euler": [0, 0, -1.2]}
    b["arm.right.upper"] = {"euler": [0, 0, 1.2]}
    return {"bones": b, "meta": {"name": "arms-down"}}
