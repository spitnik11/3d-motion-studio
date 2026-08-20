"""Blender-side of the BlenderBridge — Phase 3.

Runs INSIDE Blender (its own Python 3.13). The venv-side launcher
(server/blender_bridge.py) invokes:

    blender --background [scene.blend] --python bridge_ops.py -- <commands.json> <result.json>

Each command is {"op": "...", ...args}. Results are written to <result.json> as a
list of {"ok": bool, "op": str, ...} — one per command, in order. A failing
command records the error and the batch continues, so a test can inspect exactly
where it broke.

Only validated ops are exposed here; there is deliberately NO "run arbitrary
Python" op (see integration-boundaries.md).
"""

import json
import sys

import bpy
from mathutils import Euler


# ---- helpers ---------------------------------------------------------------

def _obj(name):
    o = bpy.data.objects.get(name)
    if o is None:
        raise KeyError(f"no object named {name!r}")
    return o


def _reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


# ---- op handlers -----------------------------------------------------------

def op_health(_):
    return {"blender": bpy.app.version_string, "objects": len(bpy.data.objects)}


def op_newScene(_):
    _reset_scene()
    return {}


def op_createObject(cmd):
    kind = cmd.get("kind", "empty")
    name = cmd["name"]
    loc = tuple(cmd.get("location", (0, 0, 0)))
    if kind == "cube":
        bpy.ops.mesh.primitive_cube_add(location=loc)
    elif kind == "empty":
        bpy.ops.object.empty_add(location=loc)
    else:
        raise ValueError(f"unknown object kind {kind!r}")
    bpy.context.active_object.name = name
    return {"name": name}


def op_setTransform(cmd):
    o = _obj(cmd["name"])
    if "location" in cmd:
        o.location = tuple(cmd["location"])
    if "rotation_euler" in cmd:
        o.rotation_euler = tuple(cmd["rotation_euler"])
    if "scale" in cmd:
        o.scale = tuple(cmd["scale"])
    return {"name": o.name}


def op_getTransform(cmd):
    o = _obj(cmd["name"])
    return {
        "name": o.name,
        "location": list(o.location),
        "rotation_euler": list(o.rotation_euler),
        "scale": list(o.scale),
    }


def op_selectObject(cmd):
    bpy.ops.object.select_all(action="DESELECT")
    o = _obj(cmd["name"])
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    return {"name": o.name}


def op_listObjects(_):
    return {"objects": [o.name for o in bpy.data.objects]}


def op_listArmatures(_):
    return {"armatures": [o.name for o in bpy.data.objects if o.type == "ARMATURE"]}


def op_importModel(cmd):
    path = cmd["path"]
    lower = path.lower()
    if lower.endswith((".glb", ".gltf")):
        bpy.ops.import_scene.gltf(filepath=path)
    elif lower.endswith(".fbx"):
        bpy.ops.import_scene.fbx(filepath=path)
    elif lower.endswith(".obj"):
        bpy.ops.wm.obj_import(filepath=path)
    elif lower.endswith(".bvh"):
        bpy.ops.import_anim.bvh(filepath=path)
    else:
        raise ValueError(f"unsupported import format: {path}")
    return {"objects": [o.name for o in bpy.context.selected_objects]}


def op_setBoneRotation(cmd):
    """Rotate a pose bone (radians, XYZ euler) on an armature object."""
    arm = _obj(cmd["armature"])
    pbone = arm.pose.bones.get(cmd["bone"])
    if pbone is None:
        raise KeyError(f"no bone {cmd['bone']!r} on {cmd['armature']!r}")
    pbone.rotation_mode = "XYZ"
    pbone.rotation_euler = Euler(tuple(cmd["euler"]), "XYZ")
    return {"bone": pbone.name}


def op_setBoneLocation(cmd):
    arm = _obj(cmd["armature"])
    pbone = arm.pose.bones.get(cmd["bone"])
    if pbone is None:
        raise KeyError(f"no bone {cmd['bone']!r} on {cmd['armature']!r}")
    pbone.location = tuple(cmd["location"])
    return {"bone": pbone.name}


def op_getBoneRotation(cmd):
    arm = _obj(cmd["armature"])
    pbone = arm.pose.bones.get(cmd["bone"])
    if pbone is None:
        raise KeyError(f"no bone {cmd['bone']!r}")
    return {"bone": pbone.name, "euler": list(pbone.rotation_euler)}


def op_setFrame(cmd):
    bpy.context.scene.frame_set(int(cmd["frame"]))
    return {"frame": bpy.context.scene.frame_current}


def op_insertKeyframe(cmd):
    """Keyframe a pose bone's rotation/location at the given frame."""
    arm = _obj(cmd["armature"])
    pbone = arm.pose.bones.get(cmd["bone"])
    if pbone is None:
        raise KeyError(f"no bone {cmd['bone']!r}")
    frame = int(cmd["frame"])
    for path in cmd.get("paths", ["rotation_euler"]):
        pbone.keyframe_insert(data_path=path, frame=frame)
    return {"bone": pbone.name, "frame": frame}


def op_setCamera(cmd):
    cam = bpy.data.objects.get(cmd.get("name", "Camera"))
    if cam is None or cam.type != "CAMERA":
        cam_data = bpy.data.cameras.new(cmd.get("name", "Camera"))
        cam = bpy.data.objects.new(cmd.get("name", "Camera"), cam_data)
        bpy.context.scene.collection.objects.link(cam)
    if "location" in cmd:
        cam.location = tuple(cmd["location"])
    if "rotation_euler" in cmd:
        cam.rotation_euler = tuple(cmd["rotation_euler"])
    bpy.context.scene.camera = cam
    return {"name": cam.name}


def op_renderPreview(cmd):
    scene = bpy.context.scene
    scene.render.filepath = cmd["path"]
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_x = int(cmd.get("width", 512))
    scene.render.resolution_y = int(cmd.get("height", 512))
    bpy.ops.render.render(write_still=True)
    return {"path": cmd["path"]}


def op_saveProject(cmd):
    bpy.ops.wm.save_as_mainfile(filepath=cmd["path"])
    return {"path": cmd["path"]}


def op_createSnapshot(cmd):
    """A snapshot is just a saved .blend copy (Blender is the source of truth)."""
    bpy.ops.wm.save_as_mainfile(filepath=cmd["path"], copy=True)
    return {"path": cmd["path"]}


# ponytail: no live undo in batch mode; createSnapshot/restoreSnapshot cover it.
# Add a socket-served long-lived session when the interactive Pose Studio (Phase 6+) needs it.

OPS = {name[3:]: fn for name, fn in globals().items() if name.startswith("op_")}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    commands = json.loads(open(argv[0], encoding="utf-8").read())
    results = []
    for cmd in commands:
        op = cmd.get("op")
        try:
            handler = OPS.get(op)
            if handler is None:
                raise ValueError(f"unknown op {op!r}")
            data = handler(cmd)
            results.append({"ok": True, "op": op, **data})
        except Exception as e:  # noqa: BLE001 — report, don't crash the batch
            results.append({"ok": False, "op": op, "error": f"{type(e).__name__}: {e}"})
    with open(argv[1], "w", encoding="utf-8") as f:
        json.dump(results, f)


if __name__ == "__main__":
    main()
