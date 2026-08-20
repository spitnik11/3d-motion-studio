"""Close the AI loop: a generated prop → approved PropAsset → composed into a posed
multi-character scene → PoseBundle. Proves AI-generated assets flow through to the
real pipeline (the same PoseBundle that goes to Comfy).

Uses a real SPAR3D-generated mesh if present, else authors a cube stand-in in Blender.

Run: python tests/test_compose.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.blender_bridge import BlenderBridge  # noqa: E402
from server.registry.registry import AssetRegistry  # noqa: E402
from server.mesh_pipeline import stage_unapproved, validate_mesh, approve, _UNAPPROVED  # noqa: E402
from server.composer import compose_and_export  # noqa: E402
from server.posing import apply_pose_commands  # noqa: E402
import shutil  # noqa: E402

GENERATED = "Z:/ai-assets/spar3d-out/0/mesh.glb"  # a real generated prop, if present


def _prop_mesh(bridge, tmp):
    """Prefer a real generated mesh; else author a cube glb (download-free)."""
    if Path(GENERATED).is_file():
        return GENERATED, "spar3d-mesh"
    glb = str(Path(tmp) / "prop.glb")
    bridge.run([{"op": "newScene"}, {"op": "createObject", "kind": "cube", "name": "Prop"},
                {"op": "exportGLB", "path": glb}])
    return glb, "cube-prop"


def test_close_loop_generated_prop_into_posebundle():
    bridge = BlenderBridge()
    with tempfile.TemporaryDirectory() as tmp:
        mesh, tag = _prop_mesh(bridge, tmp)

        # Approve the generated mesh into the registry (the only path in).
        registry = AssetRegistry(":memory:")
        pending = stage_unapproved(mesh, source=tag, provider="spar3d")
        try:
            v = validate_mesh(pending, bridge)
            assert v["ok"], v
            prop = approve(pending, registry, name="GeneratedProp")
            assert prop["kind"] == "PropAsset"

            # Compose: posed 2-character scene + the approved prop between them.
            manifest = {"ground": True, "lights": [{"type": "SUN", "name": "Key"}],
                        "camera": "full body", "subjectX": 0.3,
                        "actors": [{"name": "A", "offset": [0, 0, 0]},
                                   {"name": "B", "offset": [0.8, 0, 0]}]}
            poses = {"A": {"bones": {"arm.right.upper": {"euler": [0, 0, 0.5]}}},
                     "B": {"bones": {"arm.left.upper": {"euler": [0, 0, -0.5]}}}}
            props = [{"path": prop["localPath"], "name": "TheProp",
                      "location": [0.4, 0, 1.0], "scale": 0.4}]

            bundle = str(Path(tmp) / "bundle")
            res = compose_and_export(
                bridge, manifest=manifest, bundle_dir=bundle, frames=[1],
                actors=[{"name": "A", "index": 1}, {"name": "B", "index": 2}],
                props=props, poses=poses, width=256, height=256)
            assert res["valid"], res["errors"]

            # The generated prop is actually in the composed scene.
            objs = bridge.run([{"op": "listObjects"}], blend_in=res["blend"])[0]["objects"]
            assert "TheProp" in objs, f"generated prop not in scene: {objs}"
            print(f"AI loop closed: generated prop ({tag}) -> PoseBundle (valid={res['valid']})")
        finally:
            shutil.rmtree(_UNAPPROVED / pending["id"], ignore_errors=True)


if __name__ == "__main__":
    test_close_loop_generated_prop_into_posebundle()
    print("AI loop closure (props): gate passes")
