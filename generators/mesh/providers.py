"""Mesh-generation providers — Phase 20 (framework) / 21 (Hunyuan).

Each provider wraps a local AI mesh model (Stable Fast 3D, SPAR3D, Hunyuan3D). They
are DISABLED until their model + isolated environment are installed; asking a disabled
provider to generate raises NotAvailable rather than crashing. Never merge these deps
into Blender's Python — dedicated env or the :8190 experimental Comfy.
"""

from __future__ import annotations

from server.capabilities import Capabilities


class NotAvailable(RuntimeError):
    pass


class MeshProvider:
    key = ""            # capabilities.meshGeneration.<key>
    name = ""

    def __init__(self, caps: Capabilities | None = None):
        self.caps = caps or Capabilities()

    @property
    def available(self) -> bool:
        return self.caps.enabled(f"meshGeneration.{self.key}")

    def generate(self, image_path: str, out_path: str) -> str:
        if not self.available:
            raise NotAvailable(
                f"{self.name} disabled — enable capabilities.meshGeneration.{self.key} "
                "after installing the model in an isolated env")
        return self._generate(image_path, out_path)

    def _generate(self, image_path: str, out_path: str) -> str:  # pragma: no cover
        raise NotImplementedError


class StableFast3DProvider(MeshProvider):
    key, name = "stableFast3d", "Stable Fast 3D"


class Spar3DProvider(MeshProvider):
    key, name = "spar3d", "SPAR3D"


class Hunyuan3DProvider(MeshProvider):
    key, name = "hunyuan", "Hunyuan3D 2.1"


PROVIDERS = {p.key: p for p in (StableFast3DProvider, Spar3DProvider, Hunyuan3DProvider)}


def get_provider(key: str, caps: Capabilities | None = None) -> MeshProvider:
    if key not in PROVIDERS:
        raise KeyError(f"unknown mesh provider {key!r}; have {sorted(PROVIDERS)}")
    return PROVIDERS[key](caps)
