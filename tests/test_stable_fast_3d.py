"""Phase 20 LIVE: Stable Fast 3D actually generates a mesh, and the full pipeline
(generate → stage-unapproved → validate-in-Blender → approve → registry) runs on it.

Uses the installed Z:/ai-envs/stable-fast-3d env (torch cu130, sm_120) + gated weights.
Skips if the env/weights or capability aren't present. Real GPU generation — slow.

Run: python tests/test_stable_fast_3d.py
"""

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.registry.registry import AssetRegistry  # noqa: E402
from server.mesh_pipeline import stage_unapproved, validate_mesh, approve, _UNAPPROVED  # noqa: E402
from generators.mesh.providers import get_provider  # noqa: E402

# A clean example object shipped with the repo (a real prop image).
EXAMPLE = "Z:/ai-repos/stable-fast-3d/demo_files/examples/axe.png"


def test_phase20_stable_fast_3d_live():
    prov = get_provider("stableFast3d")
    if not prov.available:
        print("SKIP: Stable Fast 3D env/capability not available")
        return
    if not Path(EXAMPLE).is_file():
        print("SKIP: example image missing")
        return

    with tempfile.TemporaryDirectory() as tmp:
        out_mesh = str(Path(tmp) / "prop.glb")
        prov.generate(EXAMPLE, out_mesh)                 # real GPU image→3D
        assert Path(out_mesh).stat().st_size > 0, "no mesh produced"

        registry = AssetRegistry(":memory:")
        pending = stage_unapproved(out_mesh, source="axe.png", provider="stableFast3d")
        try:
            assert registry.all("PropAsset") == []       # unapproved: not in registry yet
            v = validate_mesh(pending)                    # Blender import + geometry check
            assert v["ok"] and v["verts"] > 100 and v["faces"] > 100, v
            rec = approve(pending, registry, name="GeneratedAxe")
            assert rec["kind"] == "PropAsset" and rec["payload"]["generated"] is True
            assert len(registry.all("PropAsset")) == 1
            print(f"generated + approved mesh: {v['verts']} verts / {v['faces']} faces")
        finally:
            shutil.rmtree(_UNAPPROVED / pending["id"], ignore_errors=True)


def test_phase20_spar3d_live():
    prov = get_provider("spar3d")
    if not prov.available:
        print("SKIP: SPAR3D env/capability not available")
        return
    ex = "Z:/ai-repos/stable-point-aware-3d/demo_files/examples"
    from pathlib import Path as _P
    imgs = sorted(_P(ex).glob("*.png")) if _P(ex).is_dir() else []
    if not imgs:
        print("SKIP: no SPAR3D example image")
        return
    with tempfile.TemporaryDirectory() as tmp:
        out_mesh = str(Path(tmp) / "prop.glb")
        prov.generate(str(imgs[0]), out_mesh)
        assert Path(out_mesh).stat().st_size > 0
        registry = AssetRegistry(":memory:")
        pending = stage_unapproved(out_mesh, source=imgs[0].name, provider="spar3d")
        try:
            v = validate_mesh(pending)
            assert v["ok"] and v["verts"] > 100, v
            rec = approve(pending, registry, name="GeneratedSpar3D")
            assert rec["kind"] == "PropAsset"
            print(f"SPAR3D generated + approved: {v['verts']} verts / {v['faces']} faces")
        finally:
            shutil.rmtree(_UNAPPROVED / pending["id"], ignore_errors=True)


if __name__ == "__main__":
    test_phase20_stable_fast_3d_live()
    test_phase20_spar3d_live()
    print("Phase 20 Stable Fast 3D + SPAR3D: live gates pass")
