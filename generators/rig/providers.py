"""Auto-rig providers — Phase 23 (UniRig). LIVE: skeleton prediction stage.

UniRig runs in its own isolated env (Z:/ai-envs/unirig, py3.11, torch cu130). The
skeleton stage works on the Blackwell GPU (spconv via cumm JIT, torch_scatter/cluster
source-built for sm_120, sdpa attention instead of flash_attn). The skinning stage
still needs real flash_attn (Windows-hostile) — skeleton is the live capability.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from generators.gated import GatedProvider

UNIRIG_ENV_PY = Path("Z:/ai-envs/unirig/Scripts/python.exe")
UNIRIG_REPO = Path("Z:/ai-repos/UniRig")
_HF_HUB_CACHE = "Z:/ai-models/hf"
_SKELETON_TASK = "configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml"


class UniRigProvider(GatedProvider):
    cap_path, name = "autoRig.unirig", "UniRig"
    env_python = UNIRIG_ENV_PY

    @property
    def available(self) -> bool:
        return self.caps.enabled(self.cap_path) and self.env_python.is_file()

    def rig(self, mesh_path: str, out_path: str, *, seed: int = 12345) -> str:
        """Predict a skeleton (armature) for a mesh → write skeleton FBX to out_path.

        UniRig derives the npz/output paths from the input's REPO-RELATIVE path, so the
        mesh is staged under the repo and referenced relatively (matching launch scripts).
        """
        self.require()
        env = os.environ.copy()
        env["HF_HUB_CACHE"] = _HF_HUB_CACHE
        ext = Path(mesh_path).suffix
        stage = UNIRIG_REPO / "_prov_in"
        shutil.rmtree(stage, ignore_errors=True)
        stage.mkdir(parents=True, exist_ok=True)
        rel_input = f"_prov_in/mesh{ext}"
        shutil.copy2(mesh_path, UNIRIG_REPO / rel_input)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                outdir = Path(tmp) / "out"
                common = dict(cwd=str(UNIRIG_REPO), env=env, check=True,
                              capture_output=True, text=True)
                subprocess.run([str(self.env_python), "-m", "src.data.extract",
                                "--config=configs/data/quick_inference.yaml",
                                "--require_suffix=obj,fbx,FBX,dae,glb,gltf,vrm",
                                "--force_override=true", "--num_runs=1", "--id=0", "--time=run",
                                "--faces_target_count=50000", f"--input={rel_input}",
                                "--output_dir=tmp"], **common)
                subprocess.run([str(self.env_python), "run.py", f"--task={_SKELETON_TASK}",
                                f"--seed={seed}", f"--input={rel_input}",
                                f"--output_dir={outdir}"], **common)
                fbxs = list(outdir.rglob("skeleton.fbx"))
                if not fbxs:
                    raise RuntimeError("UniRig produced no skeleton")
                Path(out_path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(fbxs[0], out_path)
        finally:
            shutil.rmtree(stage, ignore_errors=True)
        return out_path
