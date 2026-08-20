"""Agent pose + animation assist — Phases 26-27.

The agent PROPOSES; the human disposes. propose_* returns a pose/breakdown proposal
(pure data); the caller Accepts (apply via AgentHistory), Rejects (drop it), Reverts
(AgentHistory.undo), or Edits (mutate the dict first). Proposals never touch locked
bones, and the agent never regenerates finished manual motion on its own.
"""

from __future__ import annotations


# ---- pose assist (Phase 26) -------------------------------------------------
def propose_pose(goal: str, *, locks=None) -> dict:
    """Heuristic pose proposal for a natural-language goal. Skips locked bones."""
    locks = set(locks or [])
    g = goal.lower()
    bones: dict = {}
    meta = {"goal": goal}

    if "wider" in g or "widen" in g or "stance" in g:
        bones = {"leg.left.upper": {"euler": [0, 0, 0.3]},
                 "leg.right.upper": {"euler": [0, 0, -0.3]}}
    elif "balance" in g:
        # Center pelvis/spine roll — a stability nudge, not a rewrite.
        bones = {"pelvis": {"euler": [0.0, 0.0, 0.0]},
                 "spine.lower": {"euler": [0.0, 0.0, 0.0]}}
    elif "feet planted" in g or "plant" in g:
        meta["suggestLocks"] = ["foot.left", "foot.right"]
    elif "arms down" in g or "relax arms" in g:
        bones = {"arm.left.upper": {"euler": [0, 0, -0.2]},
                 "arm.right.upper": {"euler": [0, 0, 0.2]}}
    else:
        raise ValueError(f"no proposal heuristic for goal {goal!r}")

    return {"bones": {k: v for k, v in bones.items() if k not in locks}, "meta": meta}


# ---- animation assist (Phase 27) --------------------------------------------
def propose_breakdown(pose_a: dict, pose_b: dict, t: float = 0.5, *, locks=None) -> dict:
    """Interpolate a breakdown between two key poses. Locked bones are left out so the
    agent works AROUND the artist's manual edits."""
    locks = set(locks or [])
    a, b = pose_a.get("bones", {}), pose_b.get("bones", {})
    bones = {}
    for name in set(a) | set(b):
        if name in locks:
            continue
        ea = a.get(name, {}).get("euler", [0, 0, 0])
        eb = b.get(name, {}).get("euler", [0, 0, 0])
        bones[name] = {"euler": [x + (y - x) * t for x, y in zip(ea, eb)]}
    return {"bones": bones, "meta": {"breakdown": t}}


def retime(keyframes: dict[int, dict], scale: float) -> dict[int, dict]:
    """Retime an action: frame -> pose becomes round(frame*scale) -> pose."""
    return {max(1, round(f * scale)): pose for f, pose in sorted(keyframes.items())}
