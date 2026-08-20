"""Motion import + retargeting — Phase 12.

Import a MotionAsset (BVH / FBX-anim / Blender action) and retarget it onto a target
character through the SemanticRig layer. Imported motion stays standard Blender
animation data, so it remains editable after retargeting.
"""

from __future__ import annotations

from characters.semantic_rig import CANONICAL_BODY
from server.registry.registry import AssetRegistry


def register_motion(registry: AssetRegistry, name: str, path: str, *, source: str = "",
                    frames: int = 0, **provenance) -> dict:
    return registry.register("MotionAsset", name, source=source, localPath=path,
                             format=path.rsplit(".", 1)[-1].lower(),
                             payload={"frames": frames}, **provenance)


def retarget_commands(source: str, target: str, *, source_family="canonical",
                      target_family="canonical", frames=None, bones=None) -> list[dict]:
    return [{
        "op": "retargetMotion",
        "source": source, "target": target,
        "sourceFamily": source_family, "targetFamily": target_family,
        "bones": bones or CANONICAL_BODY,
        **({"frames": frames} if frames else {}),
    }]
