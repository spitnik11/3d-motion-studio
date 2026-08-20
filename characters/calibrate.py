"""Skeleton auto-calibration — map a generic predicted skeleton (e.g. UniRig's
bone_0..bone_N) onto SemanticRig canonical humanoid bones.

Heuristic and approximate — Phase 5 always said unknown rigs enter a calibration step;
this gives a best-effort automatic mapping so a generated+rigged humanoid becomes
poseable, which a UI can then refine. Pure Python (operates on the armatureGraph).
"""

from __future__ import annotations


def _axes(heads):
    """Return (up, lateral, depth) axis indices by spatial spread."""
    rng = [max(h[i] for h in heads.values()) - min(h[i] for h in heads.values()) for i in range(3)]
    up = rng.index(max(rng))
    others = [i for i in range(3) if i != up]
    lat = max(others, key=lambda i: rng[i])
    depth = [i for i in others if i != lat][0]
    return up, lat, depth


def calibrate_skeleton(graph_bones: list[dict]) -> dict:
    """graph_bones: [{name, parent, head, tail}]. Returns
    {"mapping": {canonical: bone}, "coverage": float, "up": axis, "lateral": axis}."""
    bones = {b["name"]: b for b in graph_bones}
    heads = {n: b["head"] for n, b in bones.items()}
    if not heads:
        return {"mapping": {}, "coverage": 0.0}
    up, lat, depth = _axes(heads)

    def U(n): return heads[n][up]
    def LAT(n): return heads[n][lat]

    parent = {n: b["parent"] for n, b in bones.items()}
    children: dict[str, list[str]] = {}
    for n, p in parent.items():
        if p is not None:
            children.setdefault(p, []).append(n)

    roots = [n for n, p in parent.items() if p is None] or [min(heads, key=U)]
    root = roots[0]
    head_bone = max(heads, key=U)

    def path_to_root(n):
        p = [n]
        while parent.get(n) is not None:
            n = parent[n]
            p.append(n)
        return list(reversed(p))

    spine_path = path_to_root(head_bone)  # central chain root..head
    mapping: dict[str, str] = {"root": root}
    spine_slots = ["pelvis", "spine.lower", "spine.middle", "spine.upper", "neck", "head"]
    n = len(spine_path)
    for i, slot in enumerate(spine_slots):
        idx = round(i * (n - 1) / (len(spine_slots) - 1)) if n > 1 else 0
        mapping[slot] = spine_path[idx]
    mapping["head"] = head_bone

    spine_set = set(spine_path)
    up_thresh = U(mapping["spine.upper"])
    pelvis_z = U(mapping["pelvis"])

    # leaves = bones with no children
    leaves = [n for n in bones if n not in children]

    def chain_from_spine(leaf):
        c = [leaf]
        while parent.get(leaf) is not None and parent[leaf] not in spine_set:
            leaf = parent[leaf]
            c.append(leaf)
        return list(reversed(c))  # from near-spine to tip

    def assign_limb(prefix, chain, slots):
        m = {}
        k = len(chain)
        for i, slot in enumerate(slots):
            idx = round(i * (k - 1) / (len(slots) - 1)) if k > 1 else 0
            m[f"{prefix}{slot}"] = chain[idx]
        return m

    # Arms: leaves in upper region, split by lateral sign; take the most-lateral per side.
    arm_leaves = [lf for lf in leaves if U(lf) >= up_thresh - 0.15 * (U(head_bone) - pelvis_z)]
    for side, sign in (("left", 1), ("right", -1)):
        cand = [lf for lf in arm_leaves if (LAT(lf) * sign) > 0]
        if cand:
            tip = max(cand, key=lambda lf: abs(LAT(lf)))
            chain = chain_from_spine(tip)
            mapping.update(assign_limb(f"", chain,
                           [f"shoulder.{side}", f"arm.{side}.upper", f"arm.{side}.lower", f"hand.{side}"]))

    # Legs: leaves in lower region, split by lateral sign; the lowest per side.
    leg_leaves = [lf for lf in leaves if U(lf) < pelvis_z]
    for side, sign in (("left", 1), ("right", -1)):
        cand = [lf for lf in leg_leaves if (LAT(lf) * sign) >= 0]
        if cand:
            tip = min(cand, key=U)
            chain = chain_from_spine(tip)
            mapping.update(assign_limb(f"", chain,
                           [f"leg.{side}.upper", f"leg.{side}.lower", f"foot.{side}", f"toe.{side}"]))

    # coverage vs the core humanoid slots
    core = ["root", "pelvis", "spine.lower", "spine.upper", "head",
            "arm.left.upper", "arm.right.upper", "leg.left.upper", "leg.right.upper"]
    covered = sum(1 for c in core if c in mapping)
    return {"mapping": mapping, "coverage": covered / len(core), "up": up, "lateral": lat}
