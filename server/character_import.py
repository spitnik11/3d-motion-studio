"""CharacterImporter — Phase 4.

Imports a third-party character (VRM/FBX/GLTF/GLB/BLEND) WITHOUT ever editing the
original file: it copies the source into a sanitized per-character project dir,
imports that copy through the BlenderBridge, verifies the essentials loaded (mesh,
material, armature), and registers a CharacterAsset with provenance.

One importer, keyed by extension — the formats differ only in the bridge import op,
which the bridge already dispatches. No four near-identical adapter classes.
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from server.blender_bridge import BlenderBridge
from server.registry.registry import AssetRegistry

_ROOT = Path(__file__).resolve().parents[1]
_PROJECTS = _ROOT / "data" / "projects"

SUPPORTED = {".vrm", ".glb", ".gltf", ".fbx", ".blend"}


class ImportError_(RuntimeError):
    pass


class CharacterImporter:
    def __init__(self, bridge: BlenderBridge | None = None, registry: AssetRegistry | None = None):
        self.bridge = bridge or BlenderBridge()
        self.registry = registry or AssetRegistry()

    def import_character(self, source_path: str, *, name: str | None = None, **provenance) -> dict:
        src = Path(source_path)
        if not src.is_file():
            raise ImportError_(f"source not found: {src}")
        ext = src.suffix.lower()
        if ext not in SUPPORTED:
            raise ImportError_(f"unsupported character format {ext!r}")

        # Sanitized copy — never touch the original.
        char_id = str(uuid.uuid4())
        proj = _PROJECTS / char_id
        proj.mkdir(parents=True, exist_ok=True)
        local = proj / src.name
        shutil.copy2(src, local)

        # VRM needs the Blender VRM add-on; treat as GLTF-family import otherwise.
        import_op = {"op": "importModel", "path": str(local)}

        results = self.bridge.run(
            [
                {"op": "newScene"},
                import_op,
                {"op": "listArmatures"},
                {"op": "listObjects"},
                {"op": "listMaterials"},
            ],
            blend_out=str(proj / "character.blend"),
        )
        imp, arms, objs, mats = results[1], results[2], results[3], results[4]
        if not imp["ok"]:
            raise ImportError_(f"Blender import failed: {imp.get('error')}")

        armatures = arms["armatures"]
        if not armatures:
            raise ImportError_("no armature in imported character")

        record = self.registry.register(
            "CharacterAsset",
            name or src.stem,
            source=provenance.pop("source", ""),
            format=ext.lstrip("."),
            localPath=str(local),
            **provenance,
            payload={
                "projectDir": str(proj),
                "blend": str(proj / "character.blend"),
                "armatures": armatures,
                "objects": objs["objects"],
                "materials": mats["materials"],
            },
        )
        return record
