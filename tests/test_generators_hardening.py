"""Gates for Phases 20, 21, 35.

 20 generated mesh: stage(unapproved) -> validate -> approve -> registry; provider gated
 21 disabling Hunyuan has zero effect on manual posing
 35 diagnostics report health + degradation; manual posing never depends on AI caps

Run: python tests/test_generators_hardening.py
"""

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.blender_bridge import BlenderBridge  # noqa: E402
from server.registry.registry import AssetRegistry  # noqa: E402
from server.capabilities import Capabilities  # noqa: E402
from server.diagnostics import diagnostics, check_comfy  # noqa: E402
from server.mesh_pipeline import stage_unapproved, validate_mesh, approve, _UNAPPROVED  # noqa: E402
from generators.mesh.providers import get_provider, NotAvailable  # noqa: E402


def test_phase20_generated_mesh_pipeline():
    bridge = BlenderBridge()
    # A disabled provider must refuse to generate (never crash).
    prov = get_provider("stableFast3d")
    assert prov.available is False
    try:
        prov.generate("ref.png", "out.glb")
        assert False, "disabled provider should raise"
    except NotAvailable:
        pass

    with tempfile.TemporaryDirectory() as tmp:
        # Stand in for an AI-generated mesh with a real Blender-authored GLB.
        glb = str(Path(tmp) / "prop.glb")
        r = bridge.run([{"op": "newScene"},
                        {"op": "createObject", "kind": "cube", "name": "Prop"},
                        {"op": "exportGLB", "path": glb}])
        assert all(x["ok"] for x in r), r

        registry = AssetRegistry(":memory:")
        pending = stage_unapproved(glb, source="self-test", provider="stableFast3d")
        try:
            # Unapproved: staged on disk, NOT in the registry.
            assert (Path(pending["localPath"])).is_file()
            assert registry.all("PropAsset") == []

            v = validate_mesh(pending, bridge)
            assert v["ok"] and v["verts"] > 0 and v["faces"] > 0, v

            rec = approve(pending, registry, name="TestProp")
            assert rec["kind"] == "PropAsset" and rec["payload"]["generated"] is True
            assert len(registry.all("PropAsset")) == 1
        finally:
            shutil.rmtree(_UNAPPROVED / pending["id"], ignore_errors=True)


def test_phase21_hunyuan_disabled_does_not_affect_posing():
    caps = Capabilities()
    assert caps.enabled("meshGeneration.hunyuan") is False
    hun = get_provider("hunyuan", caps)
    assert hun.available is False
    try:
        hun.generate("x", "y")
        assert False
    except NotAvailable:
        pass
    # Manual posing works regardless of Hunyuan being off.
    bridge = BlenderBridge()
    r = bridge.run([{"op": "newScene"}, {"op": "createHumanoidFixture", "name": "A"},
                    {"op": "setBoneRotation", "armature": "A", "bone": "arm.left.upper", "euler": [0.4, 0, 0]},
                    {"op": "getBoneRotation", "armature": "A", "bone": "arm.left.upper"}])
    assert all(x["ok"] for x in r), r
    assert abs(r[-1]["euler"][0] - 0.4) < 1e-3


def test_phase35_diagnostics_and_degradation():
    d = diagnostics()
    assert d["blender"]["available"] is True, "Blender should be installed"
    assert d["manualPosingAvailable"] is True
    # All AI capabilities default off, and that's fine (features just disable).
    assert all(v is False for v in d["capabilities"].values())
    assert "comfy" in d["degradation"] and "frameMotion" in d["degradation"]
    # check_comfy returns a structured result whether or not Comfy is up.
    c = check_comfy()
    assert set(c) == {"available", "url", "degraded"}
    if not c["available"]:
        assert c["degraded"]


if __name__ == "__main__":
    test_phase20_generated_mesh_pipeline()
    test_phase21_hunyuan_disabled_does_not_affect_posing()
    test_phase35_diagnostics_and_degradation()
    print("Phases 20/21/35 generators + hardening: gates pass")
