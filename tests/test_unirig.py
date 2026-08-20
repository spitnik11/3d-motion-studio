"""Phase 23 LIVE: UniRig automated skeleton prediction.

Runs the isolated Z:/ai-envs/unirig env (torch cu130, spconv via cumm JIT, pyg exts
source-built for sm_120, sdpa attention). Skeleton stage only (skinning needs real
flash_attn). Skips if the env/capability/weights aren't present. Real GPU — slow.

Run: python tests/test_unirig.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.blender_bridge import BlenderBridge  # noqa: E402
from generators.rig.providers import UniRigProvider, UNIRIG_REPO  # noqa: E402

EXAMPLE = str(UNIRIG_REPO / "examples" / "giraffe.glb")


def test_phase23_unirig_skeleton_live():
    prov = UniRigProvider()
    if not prov.available:
        print("SKIP: UniRig env/capability not available")
        return
    if not Path(EXAMPLE).is_file():
        print("SKIP: no UniRig example mesh")
        return

    with tempfile.TemporaryDirectory() as tmp:
        fbx = str(Path(tmp) / "skeleton.fbx")
        prov.rig(EXAMPLE, fbx)
        assert Path(fbx).stat().st_size > 0, "no skeleton produced"

        # The skeleton FBX must contain a real armature with bones.
        bridge = BlenderBridge()
        r = bridge.run([{"op": "newScene"}, {"op": "importModel", "path": fbx},
                        {"op": "listArmatures"}])
        arms = r[2]["armatures"]
        assert arms, "no armature in UniRig skeleton"
        bones = bridge.run([{"op": "importModel", "path": fbx},
                            {"op": "listBones", "armature": arms[0]}])[1]["bones"]
        assert len(bones) >= 5, f"skeleton too small: {len(bones)} bones"
        print(f"UniRig skeleton: {len(bones)} bones")


if __name__ == "__main__":
    test_phase23_unirig_skeleton_live()
    print("Phase 23 UniRig skeleton: live gate passes")
