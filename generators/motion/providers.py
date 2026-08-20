"""Motion-generation providers — Phases 28-29. Gated. Output is a MotionAsset
CANDIDATE (retarget → manual review → contact correction → approve), never final."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path

from generators.gated import GatedProvider

_ROOT = Path(__file__).resolve().parents[2]
DRIVING_ENV_PY = Path("Z:/ai-envs/driving-video/Scripts/python.exe")
_POSE_EXTRACT = _ROOT / "generators" / "motion" / "pose_extract.py"


class MoMaskProvider(GatedProvider):
    cap_path, name = "motionGeneration.momask", "MoMask"

    def generate(self, text: str, out_path: str) -> str:
        self.require()
        raise NotImplementedError


class HYMotionProvider(GatedProvider):
    cap_path, name = "motionGeneration.hymotion", "HY-Motion"

    def generate(self, text: str, out_path: str) -> str:
        self.require()
        raise NotImplementedError


class DrivingVideoProvider(GatedProvider):
    """Phase 29: video → pose sequence via mediapipe (isolated env). Keeps movement/
    timing, discards identity/background. Output = MotionAsset candidate."""
    cap_path, name = "motionGeneration.drivingVideo", "Driving Video"
    env_python = DRIVING_ENV_PY

    @property
    def available(self) -> bool:
        return self.caps.enabled(self.cap_path) and self.env_python.is_file()

    def extract(self, video_path: str, out_path: str, *, stride: int = 1) -> dict:
        self.require()
        subprocess.run(
            [str(self.env_python), str(_POSE_EXTRACT), video_path, out_path, "--stride", str(stride)],
            check=True, capture_output=True, text=True)
        return json.loads(Path(out_path).read_text())
