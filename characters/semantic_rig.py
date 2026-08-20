"""SemanticRig — Phase 5.

A canonical, model-agnostic skeleton vocabulary plus per-family name mappings.
Every pose/animation/contact in the studio is expressed in CANONICAL names; each
rig family (VRM, Rigify, Quaternius, Mixamo, MPFB) has a table translating
canonical → that rig's actual bone names. This is what lets one semantic command
("rotate arm.left.upper") apply across different characters.

Pure Python (no bpy) so both the venv side and Blender side import it. Mappings are
best-effort for common exports; an unknown rig yields unmapped bones that the
calibration UI (later) resolves by hand.
"""

from __future__ import annotations

SIDES = ("left", "right")
FINGERS = ("thumb", "index", "middle", "ring", "pinky")
FINGER_SEGS = (1, 2, 3)

# ---- canonical body bones (order = hierarchy top-down) ---------------------
CANONICAL_BODY = [
    "root", "pelvis",
    "spine.lower", "spine.middle", "spine.upper",
    "neck", "head",
]
for _s in SIDES:
    CANONICAL_BODY += [
        f"shoulder.{_s}", f"arm.{_s}.upper", f"arm.{_s}.lower", f"hand.{_s}",
    ]
for _s in SIDES:
    CANONICAL_BODY += [
        f"leg.{_s}.upper", f"leg.{_s}.lower", f"foot.{_s}", f"toe.{_s}",
    ]


def canonical_finger(side: str, finger: str, seg: int) -> str:
    return f"hand.{side}.{finger}.{seg}"


CANONICAL_FINGERS = [
    canonical_finger(s, f, n) for s in SIDES for f in FINGERS for n in FINGER_SEGS
]

CANONICAL = CANONICAL_BODY + CANONICAL_FINGERS


# ---- family mappings -------------------------------------------------------
# side token per family: (left_token, right_token)
def _side(fam_left, fam_right):
    return {"left": fam_left, "right": fam_right}


def _vrm():
    m = {
        "root": "Root", "pelvis": "hips",
        "spine.lower": "spine", "spine.middle": "chest", "spine.upper": "upperChest",
        "neck": "neck", "head": "head",
    }
    cap = {"left": "left", "right": "right"}
    fmap = {"thumb": "Thumb", "index": "Index", "middle": "Middle", "ring": "Ring", "pinky": "Little"}
    seg = {1: "Proximal", 2: "Intermediate", 3: "Distal"}
    for s in SIDES:
        p = cap[s].capitalize()
        m[f"shoulder.{s}"] = f"{cap[s]}Shoulder"
        m[f"arm.{s}.upper"] = f"{cap[s]}UpperArm"
        m[f"arm.{s}.lower"] = f"{cap[s]}LowerArm"
        m[f"hand.{s}"] = f"{cap[s]}Hand"
        m[f"leg.{s}.upper"] = f"{cap[s]}UpperLeg"
        m[f"leg.{s}.lower"] = f"{cap[s]}LowerLeg"
        m[f"foot.{s}"] = f"{cap[s]}Foot"
        m[f"toe.{s}"] = f"{cap[s]}Toes"
        for f in FINGERS:
            for n in FINGER_SEGS:
                m[canonical_finger(s, f, n)] = f"{cap[s]}{fmap[f]}{seg[n]}"
    return m


def _mixamo():
    pre = "mixamorig:"
    m = {
        "root": f"{pre}Hips", "pelvis": f"{pre}Hips",
        "spine.lower": f"{pre}Spine", "spine.middle": f"{pre}Spine1", "spine.upper": f"{pre}Spine2",
        "neck": f"{pre}Neck", "head": f"{pre}Head",
    }
    S = {"left": "Left", "right": "Right"}
    fmap = {"thumb": "Thumb", "index": "Index", "middle": "Middle", "ring": "Ring", "pinky": "Pinky"}
    for s in SIDES:
        m[f"shoulder.{s}"] = f"{pre}{S[s]}Shoulder"
        m[f"arm.{s}.upper"] = f"{pre}{S[s]}Arm"
        m[f"arm.{s}.lower"] = f"{pre}{S[s]}ForeArm"
        m[f"hand.{s}"] = f"{pre}{S[s]}Hand"
        m[f"leg.{s}.upper"] = f"{pre}{S[s]}UpLeg"
        m[f"leg.{s}.lower"] = f"{pre}{S[s]}Leg"
        m[f"foot.{s}"] = f"{pre}{S[s]}Foot"
        m[f"toe.{s}"] = f"{pre}{S[s]}ToeBase"
        for f in FINGERS:
            for n in FINGER_SEGS:
                m[canonical_finger(s, f, n)] = f"{pre}{S[s]}Hand{fmap[f]}{n}"
    return m


def _rigify():
    # Rigify metarig bone names.
    m = {
        "root": "root", "pelvis": "spine",
        "spine.lower": "spine", "spine.middle": "spine.001", "spine.upper": "spine.002",
        "neck": "spine.004", "head": "spine.006",
    }
    L = {"left": "L", "right": "R"}
    fmap = {"thumb": "thumb", "index": "f_index", "middle": "f_middle", "ring": "f_ring", "pinky": "f_pinky"}
    for s in SIDES:
        x = L[s]
        m[f"shoulder.{s}"] = f"shoulder.{x}"
        m[f"arm.{s}.upper"] = f"upper_arm.{x}"
        m[f"arm.{s}.lower"] = f"forearm.{x}"
        m[f"hand.{s}"] = f"hand.{x}"
        m[f"leg.{s}.upper"] = f"thigh.{x}"
        m[f"leg.{s}.lower"] = f"shin.{x}"
        m[f"foot.{s}"] = f"foot.{x}"
        m[f"toe.{s}"] = f"toe.{x}"
        for f in FINGERS:
            for n in FINGER_SEGS:
                m[canonical_finger(s, f, n)] = f"{fmap[f]}.0{n}.{x}"
    return m


def _quaternius():
    m = {
        "root": "Root", "pelvis": "Hips",
        "spine.lower": "Spine", "spine.middle": "Chest", "spine.upper": "UpperChest",
        "neck": "Neck", "head": "Head",
    }
    S = {"left": "L", "right": "R"}
    fmap = {"thumb": "Thumb", "index": "Index", "middle": "Middle", "ring": "Ring", "pinky": "Pinky"}
    for s in SIDES:
        x = S[s]
        m[f"shoulder.{s}"] = f"Shoulder_{x}"
        m[f"arm.{s}.upper"] = f"UpperArm_{x}"
        m[f"arm.{s}.lower"] = f"LowerArm_{x}"
        m[f"hand.{s}"] = f"Hand_{x}"
        m[f"leg.{s}.upper"] = f"UpperLeg_{x}"
        m[f"leg.{s}.lower"] = f"LowerLeg_{x}"
        m[f"foot.{s}"] = f"Foot_{x}"
        m[f"toe.{s}"] = f"Toe_{x}"
        for f in FINGERS:
            for n in FINGER_SEGS:
                m[canonical_finger(s, f, n)] = f"{fmap[f]}{n}_{x}"
    return m


def _vroid():
    # Real VRoid Studio export naming (what the Blender VRM add-on produces).
    m = {
        "root": "Root", "pelvis": "J_Bip_C_Hips",
        "spine.lower": "J_Bip_C_Spine", "spine.middle": "J_Bip_C_Chest",
        "spine.upper": "J_Bip_C_UpperChest",
        "neck": "J_Bip_C_Neck", "head": "J_Bip_C_Head",
    }
    S = {"left": "L", "right": "R"}
    fmap = {"thumb": "Thumb", "index": "Index", "middle": "Middle", "ring": "Ring", "pinky": "Little"}
    for s in SIDES:
        x = S[s]
        m[f"shoulder.{s}"] = f"J_Bip_{x}_Shoulder"
        m[f"arm.{s}.upper"] = f"J_Bip_{x}_UpperArm"
        m[f"arm.{s}.lower"] = f"J_Bip_{x}_LowerArm"
        m[f"hand.{s}"] = f"J_Bip_{x}_Hand"
        m[f"leg.{s}.upper"] = f"J_Bip_{x}_UpperLeg"
        m[f"leg.{s}.lower"] = f"J_Bip_{x}_LowerLeg"
        m[f"foot.{s}"] = f"J_Bip_{x}_Foot"
        m[f"toe.{s}"] = f"J_Bip_{x}_ToeBase"
        for f in FINGERS:
            for n in FINGER_SEGS:
                m[canonical_finger(s, f, n)] = f"J_Bip_{x}_{fmap[f]}{n}"
    return m


def _mpfb():
    # MakeHuman/MPFB "Default" rig, approximate.
    m = {
        "root": "root", "pelvis": "pelvis",
        "spine.lower": "spine01", "spine.middle": "spine02", "spine.upper": "spine03",
        "neck": "neck01", "head": "head",
    }
    S = {"left": "L", "right": "R"}
    fmap = {"thumb": "finger1", "index": "finger2", "middle": "finger3", "ring": "finger4", "pinky": "finger5"}
    for s in SIDES:
        x = S[s]
        m[f"shoulder.{s}"] = f"clavicle.{x}"
        m[f"arm.{s}.upper"] = f"upperarm01.{x}"
        m[f"arm.{s}.lower"] = f"lowerarm01.{x}"
        m[f"hand.{s}"] = f"wrist.{x}"
        m[f"leg.{s}.upper"] = f"upperleg01.{x}"
        m[f"leg.{s}.lower"] = f"lowerleg01.{x}"
        m[f"foot.{s}"] = f"foot.{x}"
        m[f"toe.{s}"] = f"toe1-1.{x}"
        for f in FINGERS:
            for n in FINGER_SEGS:
                m[canonical_finger(s, f, n)] = f"{fmap[f]}-{n}.{x}"
    return m


# Canonical family = identity (the generated fixture uses canonical bone names).
def _canonical():
    return {c: c for c in CANONICAL}


FAMILIES = {
    "canonical": _canonical(),
    "vrm": _vrm(),          # VRM humanoid-metadata names (leftUpperArm, …)
    "vroid": _vroid(),      # real VRoid export names (J_Bip_L_UpperArm, …)
    "rigify": _rigify(),
    "quaternius": _quaternius(),
    "mixamo": _mixamo(),
    "mpfb": _mpfb(),
}


class SemanticRig:
    """Binds a rig family to an armature and translates canonical ↔ family names."""

    def __init__(self, family: str):
        if family not in FAMILIES:
            raise ValueError(f"unknown rig family {family!r}; known: {sorted(FAMILIES)}")
        self.family = family
        self.map = FAMILIES[family]

    def family_bone(self, canonical: str) -> str | None:
        return self.map.get(canonical)

    def unmapped(self) -> list[str]:
        """Canonical bones with no mapping in this family — the calibration to-do list."""
        return [c for c in CANONICAL if c not in self.map]


def detect_family(bone_names) -> str | None:
    """Best-effort family guess from an armature's bone name set. None → needs calibration."""
    names = set(bone_names)
    votes = {}
    for fam, mapping in FAMILIES.items():
        if fam == "canonical":
            continue
        votes[fam] = sum(1 for v in mapping.values() if v in names)
    fam, score = max(votes.items(), key=lambda kv: kv[1])
    if score >= max(3, len(FAMILIES[fam]) // 3):
        return fam
    # Fall back to canonical if the fixture's canonical names are present.
    if sum(1 for c in CANONICAL if c in names) >= len(CANONICAL) // 2:
        return "canonical"
    return None
