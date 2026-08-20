"""Scene & camera — Phases 13-14.

Camera presets are pure numbers (independent of which characters are loaded), so the
same preset always frames identically — that's the Phase 14 gate. A SceneManifest is
a small JSON describing ground/lights/camera/actors that loads deterministically.
"""

from __future__ import annotations

# Deterministic camera presets: (location, rotation_euler XYZ radians, lens mm).
# Framed on a subject centered near (subject_x, 0, ~1.2). Not derived from characters.
CAMERA_PRESETS = {
    "full body":     ([0.0, -4.2, 1.10], [1.484, 0.0, 0.0], 50),
    "medium":        ([0.0, -3.0, 1.30], [1.484, 0.0, 0.0], 50),
    "close":         ([0.0, -1.8, 1.55], [1.520, 0.0, 0.0], 65),
    "low angle":     ([0.0, -3.0, 0.60], [1.222, 0.0, 0.0], 40),
    "high angle":    ([0.0, -3.0, 2.40], [1.833, 0.0, 0.0], 40),
    "side":          ([-3.4, 0.0, 1.30], [1.484, 0.0, -1.5708], 50),
    "three-quarter": ([-2.4, -2.4, 1.35], [1.484, 0.0, -0.7854], 50),
    "over shoulder": ([-0.5, -1.6, 1.55], [1.484, 0.0, -0.35], 60),
}


def camera_preset_commands(preset: str, name: str = "Camera", subject_x: float = 0.3) -> list[dict]:
    if preset not in CAMERA_PRESETS:
        raise ValueError(f"unknown camera preset {preset!r}; have {sorted(CAMERA_PRESETS)}")
    loc, rot, lens = CAMERA_PRESETS[preset]
    return [{"op": "setCamera", "name": name,
             "location": [loc[0] + subject_x, loc[1], loc[2]],
             "rotation_euler": rot, "lens": lens}]


def load_scene_commands(manifest: dict) -> list[dict]:
    """SceneManifest → bridge commands. Actors default to generated humanoid fixtures."""
    cmds: list[dict] = [{"op": "newScene"}]
    if manifest.get("ground", True):
        cmds.append({"op": "addGroundPlane", "name": "Ground"})
    for light in manifest.get("lights", [{"type": "SUN", "name": "Key"}]):
        cmds.append({"op": "addLight", **light})
    for actor in manifest.get("actors", []):
        cmds.append({"op": "createHumanoidFixture", "name": actor["name"],
                     "offset": actor.get("offset", [0, 0, 0])})
        if actor.get("withMesh", True):
            cmds.append({"op": "addBodyMesh", "armature": actor["name"],
                         "material": f"Skin_{actor['name']}"})
    cmds += camera_preset_commands(manifest.get("camera", "medium"),
                                   subject_x=manifest.get("subjectX", 0.3))
    return cmds
