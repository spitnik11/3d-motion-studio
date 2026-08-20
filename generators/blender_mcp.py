"""Optional Blender MCP — Phase 34. Experiment-only; gated behind the internal Agent API.

MCP may drive interactive modeling/experiments. It NEVER owns project persistence, asset
provenance, animation truth, license enforcement, or PoseBundle creation — those stay in
3D Motion Studio."""
from __future__ import annotations
from generators.gated import GatedProvider

MCP_FORBIDDEN = {"project persistence", "asset provenance", "animation truth",
                 "license enforcement", "posebundle creation"}


class BlenderMcpProvider(GatedProvider):
    cap_path, name = "blenderMcp", "Blender MCP"

    def experiment(self, prompt: str):
        self.require()
        raise NotImplementedError

    def owns(self, responsibility: str) -> bool:
        # MCP owns nothing on the forbidden list.
        return responsibility.lower() not in MCP_FORBIDDEN
