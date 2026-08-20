"""Auto-rig providers — Phase 23 (UniRig). Gated; failure falls back to manual rigging."""
from __future__ import annotations
from generators.gated import GatedProvider


class UniRigProvider(GatedProvider):
    cap_path, name = "autoRig.unirig", "UniRig"

    def rig(self, mesh_path: str, out_path: str) -> str:
        self.require()  # raises NotAvailable until installed
        raise NotImplementedError  # real call goes here once the model is present
