"""License-aware import — Phase 32.

Before a third-party asset is used, its license block is displayed. Agents may extract
and summarize license metadata; they may NOT make the approval decision. Only an
explicit human approval marks an import approved (unknown perms stay UNKNOWN).
"""

from __future__ import annotations

from server.registry.registry import permission_label

DISPLAY_FIELDS = ("creator", "source", "license")
PERMISSION_FIELDS = ("modificationAllowed", "commercialAllowed", "redistributionAllowed",
                     "matureUseAllowed")


def license_summary(provenance: dict) -> dict:
    """Agent-safe summary of an asset's license. Description only — not a decision."""
    return {
        "creator": provenance.get("creator", ""),
        "source": provenance.get("source", ""),
        "license": provenance.get("license", ""),
        "permissions": {f: permission_label(provenance.get(f)) for f in PERMISSION_FIELDS},
        "licenseSnapshot": provenance.get("licenseSnapshot", ""),
    }


def render_license_block(provenance: dict) -> str:
    s = license_summary(provenance)
    lines = [f"Creator: {s['creator'] or '—'}", f"Source: {s['source'] or '—'}",
             f"License: {s['license'] or '—'}"]
    labels = {"modificationAllowed": "Modification", "commercialAllowed": "Commercial",
              "redistributionAllowed": "Redistribution", "matureUseAllowed": "Mature use"}
    for f, label in labels.items():
        lines.append(f"{label}: {s['permissions'][f]}")
    lines.append("[Approve Import]  (human only)")
    return "\n".join(lines)


class ImportApproval:
    """Guards that agents can summarize but only a human approves."""

    def __init__(self, provenance: dict):
        self.provenance = provenance
        self.approved = False
        self.approved_by = None

    def agent_summary(self) -> dict:
        return license_summary(self.provenance)

    def approve(self, *, by: str) -> None:
        if by == "agent":
            raise PermissionError("agents may summarize licenses but not approve imports")
        self.approved = True
        self.approved_by = by
