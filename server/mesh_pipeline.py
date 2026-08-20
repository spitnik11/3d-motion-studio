"""Generated-asset pipeline — Phase 20.

reference image → AI mesh → validation → manual inspection → approve → AssetRegistry.

Generated meshes enter an UNAPPROVED staging area and NEVER a production scene until a
human approves them. Approval is the only path into the AssetRegistry.
"""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from server.blender_bridge import BlenderBridge
from server.registry.registry import AssetRegistry

_ROOT = Path(__file__).resolve().parents[1]
_UNAPPROVED = _ROOT / "data" / "unapproved"


def stage_unapproved(mesh_path: str, *, source: str, provider: str = "", meta: dict | None = None) -> dict:
    """Copy a freshly generated mesh into the unapproved area with a pending record."""
    src = Path(mesh_path)
    if not src.is_file():
        raise FileNotFoundError(src)
    pid = str(uuid.uuid4())
    d = _UNAPPROVED / pid
    d.mkdir(parents=True, exist_ok=True)
    local = d / src.name
    shutil.copy2(src, local)
    record = {"id": pid, "status": "unapproved", "source": source, "provider": provider,
              "localPath": str(local), "meta": meta or {}, "validation": None}
    (d / "pending.json").write_text(json.dumps(record, indent=2))
    return record


def validate_mesh(pending: dict, bridge: BlenderBridge | None = None) -> dict:
    """Import the staged mesh in Blender and check it has real geometry."""
    bridge = bridge or BlenderBridge()
    r = bridge.run([{"op": "newScene"}, {"op": "meshStats", "path": pending["localPath"]}])
    stats = r[1]
    if not stats.get("ok", True) and "error" in stats:
        return {"ok": False, "error": stats["error"]}
    ok = stats.get("hasGeometry", False)
    result = {"ok": ok, "verts": stats.get("verts", 0), "faces": stats.get("faces", 0),
              "meshes": stats.get("meshes", 0)}
    pending["validation"] = result
    d = _UNAPPROVED / pending["id"]
    (d / "pending.json").write_text(json.dumps(pending, indent=2))
    return result


def approve(pending: dict, registry: AssetRegistry, *, name: str, kind: str = "PropAsset",
            **provenance) -> dict:
    """Human-approved: register into the AssetRegistry. Requires prior validation OK."""
    if not (pending.get("validation") or {}).get("ok"):
        raise ValueError("cannot approve a mesh that failed or skipped validation")
    return registry.register(
        kind, name, source=pending.get("source", ""), localPath=pending["localPath"],
        format=Path(pending["localPath"]).suffix.lstrip("."),
        payload={"generated": True, "provider": pending.get("provider", ""),
                 "validation": pending["validation"]},
        **provenance,
    )


def generate_prop(provider, image_path: str, out_path: str, *, source: str = "generated") -> dict:
    """Full head of the pipeline: provider.generate (gated) → stage_unapproved."""
    mesh = provider.generate(image_path, out_path)  # raises NotAvailable if disabled
    return stage_unapproved(mesh, source=source, provider=provider.key)
