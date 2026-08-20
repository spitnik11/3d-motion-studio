"""Agent API v1 — Phase 24.

Exposes ONLY validated, semantic primitives — never arbitrary Blender Python. Agents
say "raise left arm" or apply a structured pose; they cannot run code. Each session is
one working .blend that endpoints load, edit, and re-save.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from server.blender_bridge import BlenderBridge
from server.registry.registry import AssetRegistry
from server.diagnostics import diagnostics as _diag
from server.mesh_pipeline import stage_unapproved, validate_mesh, approve
from generators.mesh.providers import get_provider as _mesh_provider
from generators.rig.providers import UniRigProvider
from generators.motion.providers import DrivingVideoProvider
from server.scene import load_scene_commands
from server.posing import apply_pose_commands
from server.contacts import apply_contacts_commands
from server.diagnostics import diagnostics
from characters.semantic_rig import CANONICAL_BODY
from contracts.posebundle import export_posebundle, validate_posebundle

_ROOT = Path(__file__).resolve().parents[2]
_SESSIONS_DIR = _ROOT / "data" / "projects" / "sessions"
_SESSIONS: dict[str, str] = {}

# Small semantic vocabulary → canonical pose (radians).
SEMANTIC_VERBS = {
    "raise left arm": {"arm.left.upper": {"euler": [0, 0, -1.4]}},
    "raise right arm": {"arm.right.upper": {"euler": [0, 0, 1.4]}},
    "lower left arm": {"arm.left.upper": {"euler": [0, 0, -0.2]}},
    "lower right arm": {"arm.right.upper": {"euler": [0, 0, 0.2]}},
    "widen stance": {"leg.left.upper": {"euler": [0, 0, 0.25]},
                     "leg.right.upper": {"euler": [0, 0, -0.25]}},
    "bow head": {"neck": {"euler": [0.4, 0, 0]}},
}

app = FastAPI(title="3D Motion Studio Agent API", version="1.0")

_UI = _ROOT / "apps" / "control-ui" / "asset-browser.html"
_CONTROL_UI = _ROOT / "apps" / "control-ui" / "control.html"
_PREVIEWS = _ROOT / "outputs" / "previews"
_PREVIEWS.mkdir(parents=True, exist_ok=True)
_registry = AssetRegistry()


def _preview_mesh(path: str, tag: str) -> str | None:
    """Render a mesh to outputs/previews/<tag>.png; return the /previews URL or None."""
    out = _PREVIEWS / f"{tag}.png"
    try:
        r = _bridge().run([
            {"op": "newScene"}, {"op": "addLight", "type": "SUN", "name": "K", "energy": 4},
            {"op": "importModel", "path": path},
            {"op": "setCamera", "name": "Cam", "location": [1.6, -1.6, 1.1],
             "rotation_euler": [1.0, 0, 0.78], "lens": 50},
            {"op": "renderPreview", "path": str(out), "width": 480, "height": 480}])
        return f"/previews/{out.name}" if all(x["ok"] for x in r) else None
    except Exception:
        return None

# Registry kind → Asset Browser category (Phase 30).
KIND_CATEGORY = {
    "CharacterAsset": "Characters", "PoseAsset": "Poses", "HandPoseAsset": "Poses",
    "PairPoseAsset": "Poses", "MotionAsset": "Motions", "SceneAsset": "Scenes",
    "PropAsset": "Props", "StyleProfile": "Styles", "RigProfile": "Rigs",
}


app.mount("/previews", StaticFiles(directory=str(_PREVIEWS)), name="previews")
_counter = {"n": 0}


def _next_tag(prefix: str) -> str:
    _counter["n"] += 1
    return f"{prefix}_{_counter['n']}"


@app.get("/", response_class=HTMLResponse)
def control_ui():
    if _CONTROL_UI.is_file():
        return _CONTROL_UI.read_text(encoding="utf-8")
    return _UI.read_text(encoding="utf-8") if _UI.is_file() else "<h1>3D Motion Studio</h1>"


@app.get("/assets-ui", response_class=HTMLResponse)
def asset_browser():
    return _UI.read_text(encoding="utf-8") if _UI.is_file() else "<h1>Asset Browser</h1>"


@app.get("/api/capabilities")
def api_capabilities():
    return _diag()


class GenMeshReq(BaseModel):
    provider: str = "stableFast3d"   # stableFast3d | spar3d
    image: str
    approve: bool = True
    name: str = "GeneratedProp"


class GenSkelReq(BaseModel):
    mesh: str


class ExtractReq(BaseModel):
    input: str


@app.post("/api/generate/mesh")
def api_generate_mesh(req: GenMeshReq):
    prov = _mesh_provider(req.provider)
    if not prov.available:
        raise HTTPException(400, f"{req.provider} not available (capability/env off)")
    if not Path(req.image).is_file():
        raise HTTPException(400, f"image not found: {req.image}")
    tag = _next_tag(req.provider)
    out = str(_PREVIEWS.parent / f"{tag}.glb")
    prov.generate(req.image, out)
    pending = stage_unapproved(out, source=Path(req.image).name, provider=req.provider)
    v = validate_mesh(pending)
    rec = None
    if req.approve and v.get("ok"):
        rec = approve(pending, _registry, name=req.name)
    return {"mesh": out, "validation": v, "preview": _preview_mesh(out, tag),
            "approved": bool(rec), "assetId": rec["id"] if rec else None}


@app.post("/api/generate/skeleton")
def api_generate_skeleton(req: GenSkelReq):
    prov = UniRigProvider()
    if not prov.available:
        raise HTTPException(400, "UniRig not available (capability/env off)")
    if not Path(req.mesh).is_file():
        raise HTTPException(400, f"mesh not found: {req.mesh}")
    tag = _next_tag("skeleton")
    out = str(_PREVIEWS.parent / f"{tag}.fbx")
    prov.rig(req.mesh, out)
    r = _bridge().run([{"op": "newScene"}, {"op": "importModel", "path": out},
                       {"op": "listArmatures"}])
    arms = r[2]["armatures"]
    bones = _bridge().run([{"op": "importModel", "path": out},
                           {"op": "listBones", "armature": arms[0]}])[1]["bones"] if arms else []
    return {"skeleton": out, "armature": arms[0] if arms else None, "boneCount": len(bones)}


@app.post("/api/extract/pose")
def api_extract_pose(req: ExtractReq):
    prov = DrivingVideoProvider()
    if not prov.available:
        raise HTTPException(400, "driving-video not available (capability/env off)")
    if not Path(req.input).is_file():
        raise HTTPException(400, f"input not found: {req.input}")
    tag = _next_tag("motion")
    out = str(_PREVIEWS.parent / f"{tag}.json")
    data = prov.extract(req.input, out)
    frames = data.get("frames", [])
    joints = [k for k, v in (frames[0]["joints"].items() if frames else [])
              if v] if frames else []
    return {"motion": out, "frameCount": len(frames), "jointsDetected": joints}


@app.get("/api/assets")
def api_assets():
    """Assets grouped by category. Cards carry NO raw filesystem path — only names/
    metadata (Phase 30). The path lives under `details`, not the card surface."""
    groups: dict[str, list] = {}
    for a in _registry.all():
        card = {"id": a["id"], "name": a["name"], "kind": a["kind"],
                "creator": a.get("creator", ""), "license": a.get("license", ""),
                "format": a.get("format", ""),
                "details": {"localPath": a.get("localPath", ""), "sha256": a.get("sha256", "")}}
        groups.setdefault(KIND_CATEGORY.get(a["kind"], "Other"), []).append(card)
    return {"categories": groups, "count": sum(len(v) for v in groups.values())}


def _bridge() -> BlenderBridge:
    return BlenderBridge()


def _session_blend(session: str) -> str:
    if session not in _SESSIONS:
        raise HTTPException(404, f"unknown session {session}")
    return _SESSIONS[session]


class SceneReq(BaseModel):
    manifest: dict


class PoseReq(BaseModel):
    session: str
    armature: str
    family: str = "canonical"
    pose: dict | None = None
    command: str | None = Field(default=None, description="semantic verb, e.g. 'raise left arm'")
    locks: list[str] = []


class ContactReq(BaseModel):
    session: str
    source_armature: str
    target_armature: str
    source_family: str = "canonical"
    target_family: str = "canonical"
    contacts: list[dict]


class BundleReq(BaseModel):
    session: str
    frames: list[int]
    actors: list[dict]
    width: int = 512
    height: int = 512


@app.get("/api/diagnostics")
def api_diagnostics():
    return diagnostics()


@app.post("/api/scenes")
def api_scenes(req: SceneReq):
    sid = str(uuid.uuid4())
    _SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    blend = str(_SESSIONS_DIR / f"{sid}.blend")
    r = _bridge().run(load_scene_commands(req.manifest) + [{"op": "listObjects"}], blend_out=blend)
    if not all(x["ok"] for x in r):
        raise HTTPException(500, f"scene build failed: {[x for x in r if not x['ok']]}")
    _SESSIONS[sid] = blend
    objects = next(x for x in r if x["op"] == "listObjects")["objects"]
    return {"session": sid, "objects": objects}


@app.get("/api/sessions/{session}")
def api_session(session: str):
    blend = _session_blend(session)
    r = _bridge().run([{"op": "listObjects"}, {"op": "listArmatures"}], blend_in=blend)
    return {"session": session, "objects": r[0]["objects"], "armatures": r[1]["armatures"]}


@app.post("/api/poses/apply")
def api_pose_apply(req: PoseReq):
    blend = _session_blend(req.session)
    if req.command is not None:
        if req.command not in SEMANTIC_VERBS:
            raise HTTPException(400, f"unknown semantic command {req.command!r}; "
                                     f"have {sorted(SEMANTIC_VERBS)}")
        pose = {"bones": SEMANTIC_VERBS[req.command]}
    elif req.pose is not None:
        pose = req.pose
    else:
        raise HTTPException(400, "provide either 'pose' or 'command'")
    cmds = apply_pose_commands(pose, req.armature, req.family, locks=set(req.locks))
    r = _bridge().run(cmds, blend_in=blend, blend_out=blend)
    if not all(x["ok"] for x in r):
        raise HTTPException(500, f"pose apply failed: {[x for x in r if not x['ok']]}")
    return {"session": req.session, "applied": len(cmds), "locked": req.locks}


@app.post("/api/contacts")
def api_contacts(req: ContactReq):
    blend = _session_blend(req.session)
    cmds = apply_contacts_commands(
        req.contacts, source_armature=req.source_armature, source_family=req.source_family,
        target_armature=req.target_armature, target_family=req.target_family)
    r = _bridge().run(cmds, blend_in=blend, blend_out=blend)
    if not all(x["ok"] for x in r):
        raise HTTPException(500, "contact apply failed")
    return {"session": req.session, "contacts": len(req.contacts)}


@app.post("/api/render/control-bundle")
def api_control_bundle(req: BundleReq):
    blend = _session_blend(req.session)
    bundle = str(_SESSIONS_DIR / f"{req.session}_bundle")
    export_posebundle(_bridge(), blend_in=blend, bundle_dir=bundle, frames=req.frames,
                      actors=req.actors, canonical_bones=CANONICAL_BODY,
                      width=req.width, height=req.height)
    ok, errors = validate_posebundle(bundle)
    return {"session": req.session, "bundle": bundle, "valid": ok, "errors": errors}
