"""Mesh-generation providers — Phase 20 (framework) / 21 (Hunyuan).

Each provider wraps a local AI mesh model (Stable Fast 3D, SPAR3D, Hunyuan3D). They
are DISABLED until their model + isolated environment are installed; asking a disabled
provider to generate raises NotAvailable rather than crashing. Never merge these deps
into Blender's Python — dedicated env or the :8190 experimental Comfy.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from server.capabilities import Capabilities

SF3D_ENV_PY = Path("Z:/ai-envs/stable-fast-3d/Scripts/python.exe")
SF3D_REPO = Path("Z:/ai-repos/stable-fast-3d")
_HF_HUB_CACHE = "Z:/ai-models/hf"
_CUDA_BIN = "C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.3/bin"


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
    """LIVE: image → textured 3D mesh via the isolated Z:/ai-envs/stable-fast-3d env
    (torch cu130, sm_120). Available only when the env exists AND the capability is on."""
    key, name = "stableFast3d", "Stable Fast 3D"
    env_python = SF3D_ENV_PY

    @property
    def available(self) -> bool:
        return self.caps.enabled(f"meshGeneration.{self.key}") and self.env_python.is_file()

    def _generate(self, image_path: str, out_path: str) -> str:
        env = os.environ.copy()
        env["HF_HUB_CACHE"] = _HF_HUB_CACHE
        env["PATH"] = _CUDA_BIN + os.pathsep + env.get("PATH", "")
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(
                [str(self.env_python), "run.py", image_path, "--output-dir", tmp],
                cwd=str(SF3D_REPO), env=env, check=True, capture_output=True, text=True)
            mesh = Path(tmp) / "0" / "mesh.glb"
            if not mesh.is_file():
                raise RuntimeError("Stable Fast 3D produced no mesh")
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(mesh, out_path)
        return out_path


class Spar3DProvider(MeshProvider):
    key, name = "spar3d", "SPAR3D"


class Hunyuan3DProvider(MeshProvider):
    key, name = "hunyuan", "Hunyuan3D 2.1"


PROVIDERS = {p.key: p for p in (StableFast3DProvider, Spar3DProvider, Hunyuan3DProvider)}


def get_provider(key: str, caps: Capabilities | None = None) -> MeshProvider:
    if key not in PROVIDERS:
        raise KeyError(f"unknown mesh provider {key!r}; have {sorted(PROVIDERS)}")
    return PROVIDERS[key](caps)
