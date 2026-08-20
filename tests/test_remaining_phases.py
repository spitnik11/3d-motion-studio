"""Gates for Phases 22, 23, 28, 29, 31, 34.

 22 generated humanoid passes deformation QA (real, on a rigged fixture)
 23 UniRig gated; failure falls back to manual (provider raises, doesn't crash)
 28 MoMask / HY-Motion gated; output is a candidate, never final
 29 driving-video provider gated
 31 Civitai registry records metadata; agents never blind-install; content separated
 34 Blender MCP gated and owns none of the truth (persistence/provenance/posebundle/…)

Run: python tests/test_remaining_phases.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.blender_bridge import BlenderBridge  # noqa: E402
from server.registry.registry import AssetRegistry  # noqa: E402
from generators.gated import NotAvailable  # noqa: E402
from generators.rig.providers import UniRigProvider  # noqa: E402
from generators.motion.providers import MoMaskProvider, HYMotionProvider, DrivingVideoProvider  # noqa: E402
from generators.blender_mcp import BlenderMcpProvider, MCP_FORBIDDEN  # noqa: E402
from generators.character_pipeline import deformation_qa  # noqa: E402
from comfy.civitai import record_civitai_model, plan_install, profiles_by_content  # noqa: E402


def test_phase22_deformation_qa():
    bridge = BlenderBridge()
    with tempfile.TemporaryDirectory() as tmp:
        blend = str(Path(tmp) / "char.blend")
        r = bridge.run([{"op": "newScene"},
                        {"op": "createHumanoidFixture", "name": "A"},
                        {"op": "addBodyMesh", "armature": "A", "name": "A_Body"}], blend_out=blend)
        assert all(x["ok"] for x in r), r
        qa = deformation_qa(blend, "A", "A_Body", bridge=bridge)
        assert qa["passed"], qa
        assert all(v["finite"] for v in qa["joints"].values())


def test_phase23_28_29_providers_gated():
    for prov in (UniRigProvider(), MoMaskProvider(), HYMotionProvider(), DrivingVideoProvider()):
        assert prov.available is False
    try:
        UniRigProvider().rig("mesh.glb", "out.glb")
        assert False
    except NotAvailable:
        pass
    for prov, call in ((MoMaskProvider(), lambda p: p.generate("walk", "o")),
                       (HYMotionProvider(), lambda p: p.generate("walk", "o")),
                       (DrivingVideoProvider(), lambda p: p.extract("v.mp4", "o"))):
        try:
            call(prov)
            assert False
        except NotAvailable:
            pass


def test_phase34_mcp_gated_and_owns_nothing():
    mcp = BlenderMcpProvider()
    assert mcp.available is False
    try:
        mcp.experiment("model a chair")
        assert False
    except NotAvailable:
        pass
    for responsibility in MCP_FORBIDDEN:
        assert mcp.owns(responsibility) is False, f"MCP must not own {responsibility}"
    assert mcp.owns("quick prototype") is True


def test_phase31_civitai_registry_no_blind_install():
    reg = AssetRegistry(":memory:")
    general = record_civitai_model(reg, "PrettyStyle", modelId="123", versionId="456",
                                   architecture="illustrious", baseModel="SDXL",
                                   contentProfile="general")
    record_civitai_model(reg, "SpicyStyle", modelId="789", architecture="pony",
                         contentProfile="mature")
    plan = plan_install(general)
    assert plan["autoInstall"] is False, "agents must never blind-install"
    assert len(profiles_by_content(reg, "general")) == 1
    assert len(profiles_by_content(reg, "mature")) == 1
    # content profile is metadata on the style, not on the skeleton system
    assert general["payload"]["contentProfile"] == "general"


if __name__ == "__main__":
    test_phase22_deformation_qa()
    test_phase23_28_29_providers_gated()
    test_phase34_mcp_gated_and_owns_nothing()
    test_phase31_civitai_registry_no_blind_install()
    print("Phases 22/23/28/29/31/34: gates pass")
