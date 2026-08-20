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
from characters.semantic_rig import (  # noqa: E402
    SIDES, FINGERS, FINGER_SEGS, canonical_finger, SemanticRig, CANONICAL,
)


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


def op_listBones(cmd):
    arm = _obj(cmd["armature"])
    return {"armature": cmd["armature"], "bones": [b.name for b in arm.data.bones]}


def op_importModel(cmd):
    path = cmd["path"]
    lower = path.lower()
    if lower.endswith((".glb", ".gltf", ".vrm")):
        # VRM is glTF-binary; native importer loads mesh+armature. The VRM add-on,
        # when installed, additionally maps the humanoid bones + spring bones.
        try:
            bpy.ops.import_scene.vrm(filepath=path)  # VRM add-on if present
        except (AttributeError, RuntimeError):
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


def op_evaluatedMeshBounds(cmd):
    """Evaluated (deformed) world bounding box of a mesh — for deformation QA."""
    o = _obj(cmd["mesh"])
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    ev = o.evaluated_get(deps)
    me = ev.to_mesh()
    if not me.vertices:
        ev.to_mesh_clear()
        return {"mesh": cmd["mesh"], "empty": True}
    mw = ev.matrix_world
    pts = [mw @ v.co for v in me.vertices]
    xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
    ev.to_mesh_clear()
    import math
    finite = all(math.isfinite(c) for c in xs + ys + zs)
    return {"mesh": cmd["mesh"], "empty": False, "finite": finite,
            "min": [min(xs), min(ys), min(zs)], "max": [max(xs), max(ys), max(zs)]}


def op_meshStats(cmd):
    """Import a mesh and report geometry stats — mesh validation for generated assets."""
    before = set(bpy.data.objects.keys())
    op_importModel({"path": cmd["path"]})
    new = [o for name, o in bpy.data.objects.items()
           if name not in before and o.type == "MESH"]
    verts = sum(len(o.data.vertices) for o in new)
    faces = sum(len(o.data.polygons) for o in new)
    return {"meshes": len(new), "verts": verts, "faces": faces,
            "hasGeometry": verts > 0 and faces > 0}


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
    if "lens" in cmd:
        cam.data.lens = float(cmd["lens"])
    bpy.context.scene.camera = cam
    return {"name": cam.name}


def _project_2d(scene, cam, world_co):
    """World coord → normalized (x,y) in [0,1] image space (y down). None if behind cam."""
    from bpy_extras.object_utils import world_to_camera_view
    co = world_to_camera_view(scene, cam, world_co)
    if co.z <= 0:
        return None
    return [round(co.x, 5), round(1.0 - co.y, 5)]


def op_projectJoints(cmd):
    """2D camera projection of an armature's canonical joints — feeds OpenPose (pose.json)."""
    scene = bpy.context.scene
    cam = scene.camera
    if cam is None:
        raise ValueError("no active camera")
    arm = _obj(cmd["armature"])
    deps = bpy.context.evaluated_depsgraph_get()
    arm_eval = arm.evaluated_get(deps)
    joints = {}
    for canonical in cmd["bones"]:
        pb = arm_eval.pose.bones.get(canonical)
        if pb is None:
            continue
        joints[canonical] = _project_2d(scene, cam, arm_eval.matrix_world @ pb.head)
    return {"armature": cmd["armature"], "joints": joints}


def op_renderControlPasses(cmd):
    """Render RGB + depth + normal + silhouette + per-actor masks for one frame.

    actors: [{"name": armature_name, "index": 1}, ...] — index tags the actor's body
    mesh for its ID mask. Deterministic: same scene state → same files.
    """
    scene = bpy.context.scene
    outdir = cmd["outdir"]
    frame = int(cmd.get("frame", scene.frame_current))
    scene.frame_set(frame)
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = int(cmd.get("width", 512))
    scene.render.resolution_y = int(cmd.get("height", 512))
    scene.render.film_transparent = True
    # Determinism: kill dithering + temporal jitter so identical state → identical pixels.
    scene.render.dither_intensity = 0.0
    scene.render.filter_size = 0.0
    scene.eevee.taa_render_samples = int(cmd.get("samples", 1))
    scene.eevee.use_taa_reprojection = False

    vl = bpy.context.view_layer
    vl.use_pass_z = True
    vl.use_pass_normal = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"

    actors = cmd.get("actors", [])
    actor_meshes = {a["index"]: [o for o in scene.objects
                                 if o.type == "MESH" and o.name.startswith(a["name"])]
                    for a in actors}
    all_meshes = [o for ms in actor_meshes.values() for o in ms]

    def direct_render(pass_name):
        scene.compositing_node_group = None
        scene.render.filepath = f"{outdir}/{pass_name}"
        bpy.ops.render.render(write_still=True)

    # depth + normal → one multilayer EXR (the File Output node writes this reliably).
    nt = bpy.data.node_groups.new("cp", "CompositorNodeTree")
    scene.compositing_node_group = nt
    nt.nodes.clear()
    rl = nt.nodes.new("CompositorNodeRLayers")
    fo = nt.nodes.new("CompositorNodeOutputFile")
    fo.directory = outdir
    fo.file_name = "passes"
    for i, (item_name, socket_names) in enumerate([("Depth", ("Depth", "Z")), ("Normal", ("Normal",))]):
        fo.file_output_items.new("RGBA", item_name)
        sock = next(rl.outputs[n] for n in socket_names if n in rl.outputs)
        nt.links.new(sock, fo.inputs[i])
    scene.render.filepath = f"{outdir}/preview"
    bpy.ops.render.render(write_still=True)  # writes preview + passes*.exr

    # silhouette (all visible) + per-actor masks (isolation) — alpha in the PNG.
    direct_render("silhouette")
    for a in actors:
        for o in all_meshes:
            o.hide_render = o not in actor_meshes[a["index"]]
        direct_render(f"actor_{a['index']}_mask")
    for o in all_meshes:
        o.hide_render = False

    return {"frame": frame, "outdir": outdir, "actors": [a["index"] for a in actors]}


def op_exportBVH(cmd):
    arm = _obj(cmd["armature"])
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    scene = bpy.context.scene
    bpy.ops.export_anim.bvh(
        filepath=cmd["path"],
        frame_start=int(cmd.get("frame_start", scene.frame_start)),
        frame_end=int(cmd.get("frame_end", scene.frame_end)),
    )
    return {"path": cmd["path"]}


def op_retargetMotion(cmd):
    """Copy a source armature's per-frame rotations onto a target via SemanticRig.

    Same-proportion retarget (local euler copy) — real and editable afterwards.
    """
    source = _obj(cmd["source"])
    target = _obj(cmd["target"])
    srig = SemanticRig(cmd.get("sourceFamily", "canonical"))
    trig = SemanticRig(cmd.get("targetFamily", "canonical"))
    bones = cmd.get("bones", CANONICAL)
    scene = bpy.context.scene
    frames = cmd.get("frames") or list(range(scene.frame_start, scene.frame_end + 1))
    written = 0
    for f in frames:
        scene.frame_set(int(f))
        bpy.context.view_layer.update()
        for c in bones:
            sb, tb = srig.family_bone(c), trig.family_bone(c)
            spb = source.pose.bones.get(sb) if sb else None
            tpb = target.pose.bones.get(tb) if tb else None
            if not spb or not tpb:
                continue
            tpb.rotation_mode = "XYZ"
            tpb.rotation_euler = spb.rotation_euler
            tpb.keyframe_insert(data_path="rotation_euler", frame=int(f))
            written += 1
    return {"target": cmd["target"], "keys": written, "frames": len(frames)}


def op_addLight(cmd):
    ltype = cmd.get("type", "SUN").upper()
    data = bpy.data.lights.new(cmd.get("name", "Light"), ltype)
    data.energy = float(cmd.get("energy", 3.0 if ltype == "SUN" else 500.0))
    obj = bpy.data.objects.new(cmd.get("name", "Light"), data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = tuple(cmd.get("location", (2, -2, 4)))
    obj.rotation_euler = tuple(cmd.get("rotation_euler", (0.6, 0.1, 0.8)))
    return {"name": obj.name}


def op_addGroundPlane(cmd):
    bpy.ops.mesh.primitive_plane_add(size=float(cmd.get("size", 20.0)),
                                     location=tuple(cmd.get("location", (0, 0, 0))))
    p = bpy.context.active_object
    p.name = cmd.get("name", "Ground")
    return {"name": p.name}


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
        # hand/foot unconnected: contact end-effectors must be free to be pinned/IK'd.
        add(f"hand.{s}", (0.72 * k, 0, 1.50), (0.82 * k, 0, 1.50), f"arm.{s}.lower", False)
        add(f"leg.{s}.upper", (0.10 * k, 0, 1.00), (0.10 * k, 0, 0.55), "pelvis")
        add(f"leg.{s}.lower", (0.10 * k, 0, 0.55), (0.10 * k, 0, 0.10), f"leg.{s}.upper", True)
        add(f"foot.{s}", (0.10 * k, 0, 0.10), (0.10 * k, 0.15, 0.05), f"leg.{s}.lower", False)
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


def op_getBoneWorldHead(cmd):
    """World head position, evaluated (so constraints like contacts are reflected)."""
    arm = _obj(cmd["armature"])
    bpy.context.view_layer.update()  # flush constraints into the evaluated depsgraph
    deps = bpy.context.evaluated_depsgraph_get()
    arm_eval = arm.evaluated_get(deps)
    pbone = arm_eval.pose.bones.get(cmd["bone"])
    if pbone is None:
        raise KeyError(f"no bone {cmd['bone']!r}")
    world = arm_eval.matrix_world @ pbone.head
    return {"bone": cmd["bone"], "world": list(world)}


def op_addCopyLocationConstraint(cmd):
    """Contact primitive: pin `bone` to `targetBone` on another armature."""
    arm = _obj(cmd["armature"])
    pbone = arm.pose.bones.get(cmd["bone"])
    if pbone is None:
        raise KeyError(f"no bone {cmd['bone']!r}")
    con = pbone.constraints.new("COPY_LOCATION")
    con.name = cmd.get("name", "contact")
    con.target = _obj(cmd["targetArmature"])
    con.subtarget = cmd["targetBone"]
    con.influence = float(cmd.get("influence", 1.0))
    return {"bone": pbone.name, "constraint": con.name}


def op_listConstraints(cmd):
    arm = _obj(cmd["armature"])
    pbone = arm.pose.bones.get(cmd["bone"])
    if pbone is None:
        raise KeyError(f"no bone {cmd['bone']!r}")
    return {"bone": pbone.name,
            "constraints": [{"name": c.name, "type": c.type} for c in pbone.constraints]}


def _action_fcurves(action):
    """Yield fcurves across both the legacy and Blender 4.4+ slotted-action APIs."""
    if hasattr(action, "fcurves") and len(action.fcurves):  # legacy
        yield from action.fcurves
        return
    for layer in getattr(action, "layers", []):
        for strip in layer.strips:
            for cbag in getattr(strip, "channelbags", []):
                yield from cbag.fcurves


def op_countKeyframes(cmd):
    """Number of keyframes on an armature's action (for animation gate)."""
    arm = _obj(cmd["armature"])
    ad = arm.animation_data
    if not ad or not ad.action:
        return {"keyframes": 0, "fcurves": 0}
    fcurves = list(_action_fcurves(ad.action))
    n = sum(len(fc.keyframe_points) for fc in fcurves)
    return {"keyframes": n, "fcurves": len(fcurves)}


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
