"""Civitai model registry — Phase 31.

Records Civitai model metadata so styles are traceable. An agent may find/record a
model but NEVER blindly installs it — plan_install always returns autoInstall=False;
a human downloads. Content profile (general vs mature) is metadata on the STYLE, kept
separate from the skeleton/animation system.
"""

from __future__ import annotations

from server.registry.registry import AssetRegistry

RECORD_FIELDS = ("source", "modelId", "versionId", "architecture", "baseModel",
                 "license", "contentProfile", "hash", "localPath")


def record_civitai_model(registry: AssetRegistry, name: str, *, source="civitai.com",
                         modelId="", versionId="", architecture="", baseModel="",
                         license="", contentProfile="general", hash="", localPath="") -> dict:
    """Register a Civitai model as a StyleProfile asset (metadata only, no download)."""
    if contentProfile not in ("general", "mature"):
        raise ValueError("contentProfile must be 'general' or 'mature'")
    return registry.register(
        "StyleProfile", name, source=source, license=license, localPath=localPath,
        payload={"modelId": modelId, "versionId": versionId, "architecture": architecture,
                 "baseModel": baseModel, "contentProfile": contentProfile, "hash": hash,
                 "installed": bool(localPath)},
    )


def plan_install(model_record: dict) -> dict:
    """Propose an install; NEVER auto-installs. A human must action it."""
    p = model_record.get("payload", {})
    return {
        "name": model_record.get("name"),
        "modelId": p.get("modelId"),
        "versionId": p.get("versionId"),
        "architecture": p.get("architecture"),
        "contentProfile": p.get("contentProfile"),
        "autoInstall": False,   # invariant: agents never blind-install
        "action": "Review and download manually into the correct model directory.",
    }


def profiles_by_content(registry: AssetRegistry, content: str) -> list[dict]:
    """Separate general-purpose vs mature-capable style profiles."""
    return [a for a in registry.all("StyleProfile")
            if a["payload"].get("contentProfile") == content]
