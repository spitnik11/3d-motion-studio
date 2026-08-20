"""Scene composer — closes the AI loop (generated assets → the real pipeline).

Assembles a scene from registry assets (posed characters + approved generated props),
places the props, and exports a PoseBundle. This is what makes the standalone AI
generators (Stable Fast 3D / SPAR3D props, UniRig skeletons) actually usable inside
the manual studio: generate → approve → compose → PoseBundle → Comfy.
"""

from __future__ import annotations

from pathlib import Path

from server.blender_bridge import BlenderBridge
from server.scene import load_scene_commands
from server.posing import apply_pose_commands
from characters.semantic_rig import CANONICAL_BODY
from contracts.posebundle import export_posebundle, validate_posebundle


def compose_scene_commands(manifest: dict, props: list[dict] | None = None,
                           poses: dict | None = None) -> list[dict]:
    """Scene from manifest + posed actors + placed props.

    props: [{"path": mesh, "name": obj, "location": [x,y,z], "scale": s}]
    poses: {actor_name: pose_dict}
    """
    cmds = load_scene_commands(manifest)
    for actor, pose in (poses or {}).items():
        cmds += apply_pose_commands(pose, actor, "canonical")
    for p in (props or []):
        cmds.append({"op": "importAndPlace", "path": p["path"],
                     "location": p.get("location", [0, 0, 0]), "scale": p.get("scale", 1.0),
                     "name": p.get("name", Path(p["path"]).stem)})
    return cmds


def compose_and_export(bridge: BlenderBridge, *, manifest: dict, bundle_dir: str,
                       frames: list[int], actors: list[dict], props: list[dict] | None = None,
                       poses: dict | None = None, width: int = 512, height: int = 512) -> dict:
    """Build a composed scene (chars + props), save it, and export a validated PoseBundle."""
    blend = str(Path(bundle_dir).resolve().parent / "composed.blend")
    Path(blend).parent.mkdir(parents=True, exist_ok=True)
    cmds = compose_scene_commands(manifest, props=props, poses=poses)
    r = bridge.run(cmds, blend_out=blend)
    if not all(x["ok"] for x in r):
        raise RuntimeError(f"compose failed: {[x for x in r if not x['ok']]}")

    export_posebundle(bridge, blend_in=blend, bundle_dir=bundle_dir, frames=frames,
                      actors=actors, canonical_bones=CANONICAL_BODY, width=width, height=height)
    ok, errors = validate_posebundle(bundle_dir)
    return {"blend": blend, "bundle": bundle_dir, "valid": ok, "errors": errors}
