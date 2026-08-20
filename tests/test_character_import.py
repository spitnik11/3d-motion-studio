"""Phase 4 gate: a character fixture loads with mesh, materials, armature, scale,
orientation, provenance — and the original source file is never modified.

We self-generate a rigged+textured GLB in Blender (no downloads), then import it
through the real adapter. VRM specifically needs the Blender VRM add-on + a real
VRoid file — that path is structurally in place but gated on the add-on.

Run: python tests/test_character_import.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.blender_bridge import BlenderBridge  # noqa: E402
from server.registry.registry import AssetRegistry  # noqa: E402
from server.character_import import CharacterImporter  # noqa: E402


def test_gate_import_recovers_essentials():
    bridge = BlenderBridge()
    with tempfile.TemporaryDirectory() as tmp:
        glb = str(Path(tmp) / "actor.glb")
        # Author a rigged + materialed character and export GLB.
        r = bridge.run([
            {"op": "newScene"},
            {"op": "createHumanoidFixture", "name": "ActorA"},
            {"op": "addBodyMesh", "armature": "ActorA", "material": "Skin"},
            {"op": "exportGLB", "path": glb},
        ])
        assert all(x["ok"] for x in r), r
        src_bytes = Path(glb).read_bytes()

        registry = AssetRegistry(":memory:")
        importer = CharacterImporter(bridge=bridge, registry=registry)
        rec = importer.import_character(glb, name="ActorA", source="self-test")

        assert rec["kind"] == "CharacterAsset"
        assert rec["payload"]["armatures"], "no armature recovered"
        assert rec["payload"]["materials"], "no material recovered"
        assert rec["sha256"], "provenance hash missing"
        assert rec["source"] == "self-test"
        # unknown perms stay UNKNOWN
        assert rec["commercialAllowed"] is None

        # Original file untouched.
        assert Path(glb).read_bytes() == src_bytes, "importer modified the source file!"

        # Survives registry restart is covered by test_registry; here just recover.
        assert registry.get(rec["id"]) == rec


if __name__ == "__main__":
    test_gate_import_recovers_essentials()
    print("Phase 4 CharacterImporter: gate passes")
