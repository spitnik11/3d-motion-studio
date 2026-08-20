"""Diagnostics & graceful degradation — Phase 35.

Reports dependency/capability health and the degradation each missing piece triggers.
The rule (plan Phase 35): optional dependency missing → disable feature, not crash.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

from server.capabilities import Capabilities, load_config

# What still works when a piece is unavailable (the plan's degradation matrix).
DEGRADATION = {
    "charMorph": "CharMorph generator hidden; other characters unaffected",
    "autoRig.unirig": "manual rigging remains",
    "meshGeneration.stableFast3d": "manual assets remain",
    "comfy": "Blender posing + PoseBundle export remain",
    "frameMotion": "PoseBundle export remains",
}


def _reachable(url: str, timeout: int = 4) -> bool:
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except Exception:
        return False


def check_blender(config: dict | None = None) -> dict:
    cfg = config or load_config()
    exe = cfg.get("blender", {}).get("executable")
    ok = bool(exe) and Path(exe).is_file()
    return {"available": ok, "executable": exe,
            "degraded": None if ok else "no manual posing until Blender 5.2 installed"}


def check_comfy(config: dict | None = None) -> dict:
    cfg = config or load_config()
    url = cfg.get("comfy", {}).get("productionUrl", "http://127.0.0.1:8188")
    ok = _reachable(url + "/system_stats")
    return {"available": ok, "url": url,
            "degraded": None if ok else DEGRADATION["comfy"]}


def check_frame_motion(config: dict | None = None) -> dict:
    cfg = config or load_config()
    url = cfg.get("frameMotion", {}).get("url", "http://127.0.0.1:3200")
    ok = _reachable(url)
    return {"available": ok, "url": url,
            "degraded": None if ok else DEGRADATION["frameMotion"]}


def diagnostics(config: dict | None = None) -> dict:
    cfg = config or load_config()
    caps = Capabilities(cfg)
    return {
        "blender": check_blender(cfg),
        "comfy": check_comfy(cfg),
        "frameMotion": check_frame_motion(cfg),
        "capabilities": caps.flat(),
        "degradation": {k: v for k, v in DEGRADATION.items()},
        # The core invariant: manual posing never depends on optional AI capabilities.
        "manualPosingAvailable": check_blender(cfg)["available"],
    }
