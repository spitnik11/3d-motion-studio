"""Motion-generation providers — Phases 28-29. Gated. Output is a MotionAsset
CANDIDATE (retarget → manual review → contact correction → approve), never final."""
from __future__ import annotations
from generators.gated import GatedProvider


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
    """Phase 29: video → pose sequence. Keeps movement/timing, discards identity/background."""
    cap_path, name = "motionGeneration.drivingVideo", "Driving Video"

    def extract(self, video_path: str, out_path: str) -> str:
        self.require()
        raise NotImplementedError
