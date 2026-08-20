"""PoseBundle v1 — the project boundary (Phase 16).

A PoseBundle is plain files: per-frame control passes + JSON metadata. Frame Motion
Studio consumes it WITHOUT Blender. This module has two halves:

- export_posebundle(): drives the bridge to render every frame's passes + joint
  projections, then writes the manifest and sidecar JSON. (Needs Blender.)
- validate_posebundle(): checks a bundle is complete and well-formed. Pure stdlib,
  NO Blender — this is the Phase 16 gate.

Layout:
    bundle/
      manifest.json          {schema:"posebundle", version:1, frames:[...], ...}
      camera.json scene.json actors.json contacts.json
      frame_0001/
        preview.png passes.exr silhouette.png actor_1_mask.png actor_2_mask.png pose.json
"""

from __future__ import annotations

import json
from pathlib import Path

SCHEMA = "posebundle"
VERSION = 1

# Files every frame directory must contain (masks are per-actor, checked separately).
REQUIRED_FRAME_FILES = ("preview.png", "passes.exr", "silhouette.png", "pose.json")


def export_posebundle(bridge, *, blend_in: str, bundle_dir: str, frames,
                      actors, canonical_bones, camera=None, scene=None,
                      contacts=None, width=512, height=512) -> dict:
    """Render passes + joint projections for each frame and write the bundle.

    actors: [{"name": armature, "index": 1}, ...]. Returns the manifest dict.
    """
    bundle = Path(bundle_dir)
    bundle.mkdir(parents=True, exist_ok=True)

    cmds = []
    for f in frames:
        fd = bundle / f"frame_{f:04d}"
        fd.mkdir(exist_ok=True)
        cmds.append({"op": "setFrame", "frame": f})
        cmds.append({"op": "renderControlPasses", "frame": f, "outdir": str(fd),
                     "width": width, "height": height, "actors": actors})
        for a in actors:
            cmds.append({"op": "projectJoints", "armature": a["name"], "bones": canonical_bones})

    results = bridge.run(cmds, blend_in=blend_in)
    for r in results:
        if not r["ok"]:
            raise RuntimeError(f"posebundle render failed: {r}")

    # Collect projectJoints results back into per-frame pose.json.
    joint_results = [r for r in results if r["op"] == "projectJoints"]
    per_frame = {f: {} for f in frames}
    k = 0
    for f in frames:
        for a in actors:
            jr = joint_results[k]; k += 1
            per_frame[f][a["name"]] = jr["joints"]
    for f in frames:
        (bundle / f"frame_{f:04d}" / "pose.json").write_text(
            json.dumps({"frame": f, "actors": per_frame[f]}, indent=2))

    manifest = {
        "schema": SCHEMA,
        "version": VERSION,
        "frames": list(frames),
        "resolution": [width, height],
        "actors": [a["name"] for a in actors],
        "actorIndices": {a["name"]: a["index"] for a in actors},
        "passes": ["preview", "depth", "normal", "silhouette", "masks", "pose"],
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (bundle / "camera.json").write_text(json.dumps(camera or {}, indent=2))
    (bundle / "scene.json").write_text(json.dumps(scene or {}, indent=2))
    (bundle / "actors.json").write_text(json.dumps({a["name"]: a for a in actors}, indent=2))
    (bundle / "contacts.json").write_text(json.dumps(contacts or [], indent=2))
    return manifest


def read_posebundle(bundle_dir: str) -> dict:
    """Load a bundle with NO Blender: manifest + sidecars + per-frame file paths.

    This is what a consumer (Frame Motion Studio) uses. Pure stdlib.
    """
    bundle = Path(bundle_dir)
    m = json.loads((bundle / "manifest.json").read_text())
    sidecars = {name: json.loads((bundle / f"{name}.json").read_text())
                for name in ("camera", "scene", "actors", "contacts")
                if (bundle / f"{name}.json").is_file()}
    indices = list(m.get("actorIndices", {}).values())
    frames = []
    for f in m.get("frames", []):
        fd = bundle / f"frame_{f:04d}"
        frames.append({
            "frame": f,
            "dir": str(fd),
            "preview": str(fd / "preview.png"),
            "passes": str(fd / "passes.exr"),
            "silhouette": str(fd / "silhouette.png"),
            "masks": {idx: str(fd / f"actor_{idx}_mask.png") for idx in indices},
            "pose": json.loads((fd / "pose.json").read_text()) if (fd / "pose.json").is_file() else None,
        })
    return {"manifest": m, "sidecars": sidecars, "frames": frames}


def validate_posebundle(bundle_dir: str) -> tuple[bool, list[str]]:
    """Blender-free completeness/format check. Returns (ok, errors)."""
    bundle = Path(bundle_dir)
    errors: list[str] = []

    mpath = bundle / "manifest.json"
    if not mpath.is_file():
        return False, ["missing manifest.json"]
    try:
        m = json.loads(mpath.read_text())
    except json.JSONDecodeError as e:
        return False, [f"manifest.json invalid JSON: {e}"]

    if m.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA!r}, got {m.get('schema')!r}")
    if m.get("version") != VERSION:
        errors.append(f"version must be {VERSION}, got {m.get('version')}")
    for side in ("camera.json", "scene.json", "actors.json", "contacts.json"):
        if not (bundle / side).is_file():
            errors.append(f"missing {side}")

    frames = m.get("frames", [])
    if not frames:
        errors.append("manifest lists no frames")
    indices = list(m.get("actorIndices", {}).values())
    for f in frames:
        fd = bundle / f"frame_{f:04d}"
        if not fd.is_dir():
            errors.append(f"missing frame dir {fd.name}")
            continue
        for fn in REQUIRED_FRAME_FILES:
            p = fd / fn
            if not p.is_file() or p.stat().st_size == 0:
                errors.append(f"{fd.name}/{fn} missing or empty")
        for idx in indices:
            p = fd / f"actor_{idx}_mask.png"
            if not p.is_file() or p.stat().st_size == 0:
                errors.append(f"{fd.name}/actor_{idx}_mask.png missing or empty")
        # pose.json must parse and carry joints for each actor
        pj = fd / "pose.json"
        if pj.is_file():
            try:
                pjd = json.loads(pj.read_text())
                if set(pjd.get("actors", {})) != set(m.get("actors", [])):
                    errors.append(f"{fd.name}/pose.json actors mismatch")
            except json.JSONDecodeError as e:
                errors.append(f"{fd.name}/pose.json invalid: {e}")

    return (not errors), errors
