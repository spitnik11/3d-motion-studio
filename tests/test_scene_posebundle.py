"""Gates for Phases 13-16. Real headless Blender for authoring/rendering; the
PoseBundle validation itself runs with NO Blender (that's the Phase 16 gate).

 13 load scene + 2 chars + lights + camera from one manifest
 14 changing characters does not move stored camera framing
 15 identical scene state -> repeatable control passes
 16 PoseBundle validates entirely outside Blender

Run: python tests/test_scene_posebundle.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.blender_bridge import BlenderBridge  # noqa: E402
from server.scene import load_scene_commands, camera_preset_commands, CAMERA_PRESETS  # noqa: E402
from server.posing import apply_pose_commands  # noqa: E402
from characters.semantic_rig import CANONICAL_BODY  # noqa: E402
from contracts.posebundle import export_posebundle, validate_posebundle  # noqa: E402

FAM = "canonical"
MANIFEST = {
    "ground": True,
    "lights": [{"type": "SUN", "name": "Key", "energy": 3.0}],
    "camera": "medium",
    "subjectX": 0.35,
    "actors": [
        {"name": "A", "offset": [0, 0, 0]},
        {"name": "B", "offset": [0.7, 0, 0]},
    ],
}


def test_phase13_load_scene_from_manifest():
    bridge = BlenderBridge()
    r = bridge.run(load_scene_commands(MANIFEST) + [{"op": "listObjects"}])
    assert all(x["ok"] for x in r), r
    objs = r[-1]["objects"]
    for need in ("Ground", "Key", "A", "B", "Camera"):
        assert need in objs, f"{need} missing from scene: {objs}"


def test_phase14_camera_preset_is_character_independent():
    # Pure function of the preset, not the characters.
    assert camera_preset_commands("medium", subject_x=0.35) == camera_preset_commands("medium", subject_x=0.35)
    a = camera_preset_commands("close")[0]
    assert a["op"] == "setCamera" and "close" in CAMERA_PRESETS
    # Applying the same preset in two different-actor scenes yields the same transform.
    bridge = BlenderBridge()
    got = []
    for actors in ([{"name": "A"}], [{"name": "A"}, {"name": "B", "offset": [0.7, 0, 0]}]):
        cmds = [{"op": "newScene"}]
        for ac in actors:
            cmds.append({"op": "createHumanoidFixture", "name": ac["name"], "offset": ac.get("offset", [0, 0, 0])})
        cmds += camera_preset_commands("medium", subject_x=0.35)
        cmds.append({"op": "getTransform", "name": "Camera"})
        r = bridge.run(cmds)
        got.append(r[-1]["location"])
    assert got[0] == got[1], f"camera framing shifted with characters: {got}"


def _build_anim_blend(bridge, blend, frames):
    cmds = load_scene_commands(MANIFEST)
    for i, f in enumerate(frames):
        t = i / max(1, len(frames) - 1)
        cmds += apply_pose_commands({"bones": {"arm.left.upper": {"euler": [t * 1.0, 0, 0]}}},
                                    "A", FAM, frame=f, keyframe=True)
        cmds += apply_pose_commands({"bones": {"arm.right.upper": {"euler": [-t * 1.0, 0, 0]}}},
                                    "B", FAM, frame=f, keyframe=True)
    r = bridge.run(cmds, blend_out=blend)
    assert all(x["ok"] for x in r), r


def test_phase15_and_16_posebundle_export_and_validate():
    bridge = BlenderBridge()
    frames = [1, 5]
    actors = [{"name": "A", "index": 1}, {"name": "B", "index": 2}]
    with tempfile.TemporaryDirectory() as tmp:
        blend = str(Path(tmp) / "anim.blend")
        _build_anim_blend(bridge, blend, frames)

        bundle = str(Path(tmp) / "bundle")
        manifest = export_posebundle(
            bridge, blend_in=blend, bundle_dir=bundle, frames=frames, actors=actors,
            canonical_bones=CANONICAL_BODY, camera={"preset": "medium"},
            scene=MANIFEST, width=128, height=128,
        )
        assert manifest["version"] == 1

        # Phase 16 gate: validate with NO Blender involved.
        ok, errors = validate_posebundle(bundle)
        assert ok, f"PoseBundle invalid: {errors}"

        # Phase 15: identical scene state -> repeatable passes (geometry silhouette).
        d1, d2 = Path(tmp) / "r1", Path(tmp) / "r2"
        for d in (d1, d2):
            d.mkdir()
            r = bridge.run([{"op": "renderControlPasses", "frame": 1, "outdir": str(d),
                             "width": 128, "height": 128, "actors": actors}], blend_in=blend)
            assert r[0]["ok"], r
        from PIL import Image  # compare PIXELS (PNG embeds a timestamp chunk)
        s1 = Image.open(d1 / "silhouette.png").tobytes()
        s2 = Image.open(d2 / "silhouette.png").tobytes()
        assert s1 == s2, "control passes not repeatable for identical scene state"
        p1 = Image.open(d1 / "preview.png").tobytes()
        p2 = Image.open(d2 / "preview.png").tobytes()
        assert p1 == p2, "RGB preview not repeatable for identical scene state"

        # Negative: a corrupt bundle fails validation.
        (Path(bundle) / "frame_0001" / "preview.png").unlink()
        ok2, errs2 = validate_posebundle(bundle)
        assert not ok2 and any("preview.png" in e for e in errs2)


if __name__ == "__main__":
    test_phase13_load_scene_from_manifest()
    test_phase14_camera_preset_is_character_independent()
    test_phase15_and_16_posebundle_export_and_validate()
    print("Phases 13-16 scene/camera/passes/PoseBundle: gates pass")
