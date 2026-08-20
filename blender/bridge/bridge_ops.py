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
from pathlib import Path

import bpy
from mathutils import Euler

# Import the shared canonical skeleton (pure-python module, no bpy).
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from characters.semantic_rig import SIDES, FINGERS, FINGER_SEGS, canonical_finger  # noqa: E402


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


def _mirror_x(v):
    return (-v[0], v[1], v[2])


def op_createHumanoidFixture(cmd):
    """Build a canonical-named humanoid armature (Actor fixture) — zero downloads.

    Bones use SemanticRig CANONICAL names, so family='canonical' is identity.
    `offset` shifts the whole rig (for placing Actor A vs Actor B).
    """
    name = cmd["name"]
    off = cmd.get("offset", (0.0, 0.0, 0.0))

    arm_data = bpy.data.armatures.new(name)
    arm = bpy.data.objects.new(name, arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones

    def add(bone_name, head, tail, parent=None, connect=False):
        b = eb.new(bone_name)
        b.head = (head[0] + off[0], head[1] + off[1], head[2] + off[2])
        b.tail = (tail[0] + off[0], tail[1] + off[1], tail[2] + off[2])
        if parent:
            b.parent = eb[parent]
            b.use_connect = connect
        return b

    # Spine chain up +Z.
    add("root", (0, 0, 0), (0, 0, 0.05))
    add("pelvis", (0, 0, 1.00), (0, 0, 1.10), "root")
    add("spine.lower", (0, 0, 1.10), (0, 0, 1.30), "pelvis", True)
    add("spine.middle", (0, 0, 1.30), (0, 0, 1.50), "spine.lower", True)
    add("spine.upper", (0, 0, 1.50), (0, 0, 1.65), "spine.middle", True)
    add("neck", (0, 0, 1.65), (0, 0, 1.75), "spine.upper", True)
    add("head", (0, 0, 1.75), (0, 0, 1.95), "neck", True)

    sign = {"left": 1.0, "right": -1.0}
    for s in SIDES:
        k = sign[s]
        add(f"shoulder.{s}", (0, 0, 1.60), (0.15 * k, 0, 1.60), "spine.upper")
        add(f"arm.{s}.upper", (0.15 * k, 0, 1.60), (0.45 * k, 0, 1.55), f"shoulder.{s}", True)
        add(f"arm.{s}.lower", (0.45 * k, 0, 1.55), (0.72 * k, 0, 1.50), f"arm.{s}.upper", True)
        add(f"hand.{s}", (0.72 * k, 0, 1.50), (0.82 * k, 0, 1.50), f"arm.{s}.lower", True)
        add(f"leg.{s}.upper", (0.10 * k, 0, 1.00), (0.10 * k, 0, 0.55), "pelvis")
        add(f"leg.{s}.lower", (0.10 * k, 0, 0.55), (0.10 * k, 0, 0.10), f"leg.{s}.upper", True)
        add(f"foot.{s}", (0.10 * k, 0, 0.10), (0.10 * k, 0.15, 0.05), f"leg.{s}.lower", True)
        add(f"toe.{s}", (0.10 * k, 0.15, 0.05), (0.10 * k, 0.25, 0.05), f"foot.{s}", True)
        # Fingers spread along Y from the hand tip.
        for fi, finger in enumerate(FINGERS):
            y = (fi - 2) * 0.03
            x0 = 0.82 * k
            parent = f"hand.{s}"
            for n in FINGER_SEGS:
                x1 = x0 + 0.03 * k
                bn = canonical_finger(s, finger, n)
                add(bn, (x0, y, 1.50), (x1, y, 1.50), parent, n > 1)
                parent = bn
                x0 = x1

    bpy.ops.object.mode_set(mode="OBJECT")
    return {"armature": name, "bones": len(arm_data.bones)}


def op_addBodyMesh(cmd):
    """Attach a simple skinned body mesh + material to an armature (fixture completeness)."""
    arm = _obj(cmd["armature"])
    off = cmd.get("offset", (0, 0, 0))
    bpy.ops.mesh.primitive_cube_add(location=(off[0], off[1], off[2] + 1.35))
    body = bpy.context.active_object
    body.name = cmd.get("name", arm.name + "_Body")
    body.scale = (0.22, 0.14, 0.85)
    mat = bpy.data.materials.new(cmd.get("material", "Skin"))
    mat.diffuse_color = (0.9, 0.75, 0.66, 1.0)
    body.data.materials.append(mat)
    # Parent to armature with automatic weights.
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    return {"mesh": body.name, "material": mat.name}


def op_listMaterials(_):
    return {"materials": [m.name for m in bpy.data.materials]}


def op_exportGLB(cmd):
    bpy.ops.export_scene.gltf(filepath=cmd["path"], export_format="GLB")
    return {"path": cmd["path"]}


def op_importScene(cmd):
    """Append/link a collection from an external .blend without running its scripts."""
    path = cmd["path"]
    with bpy.data.libraries.load(path, link=cmd.get("link", False)) as (src, dst):
        dst.objects = list(src.objects)
    linked = []
    for o in dst.objects:
        if o is not None:
            bpy.context.scene.collection.objects.link(o)
            linked.append(o.name)
    return {"objects": linked}


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
