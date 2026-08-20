"""Agent API v1 — Phase 24.

Exposes ONLY validated, semantic primitives — never arbitrary Blender Python. Agents
say "raise left arm" or apply a structured pose; they cannot run code. Each session is
one working .blend that endpoints load, edit, and re-save.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from server.blender_bridge import BlenderBridge
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
