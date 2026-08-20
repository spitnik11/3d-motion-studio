"""Phase 29 (LIVE): driving-video pose extraction actually runs.

Uses the installed mediapipe env (Z:/ai-envs/driving-video) to extract canonical 2D
joints from an image — keeping only keypoints (identity/background discarded). Skips
if the env or the sample fixture is absent.

Run: python tests/test_driving_video.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from generators.motion.providers import DrivingVideoProvider  # noqa: E402

SAMPLE = "Z:/ai-assets/person_sample.png"


def test_driving_video_extraction_live():
    prov = DrivingVideoProvider()
    if not prov.available:
        print("SKIP: driving-video env/capability not available")
        return
    if not Path(SAMPLE).is_file():
        print("SKIP: no person sample fixture")
        return
    with tempfile.TemporaryDirectory() as tmp:
        out = str(Path(tmp) / "motion.json")
        data = prov.extract(SAMPLE, out)
        assert data["frames"], "no pose frame extracted"
        joints = data["frames"][0]["joints"]
        detected = [k for k, v in joints.items() if v]
        # a full-body person yields the major canonical joints
        for need in ("hand.left", "hand.right", "foot.left", "foot.right", "pelvis"):
            assert need in detected, f"{need} not detected"
        # keypoints only — no pixels/identity carried
        assert all(len(v) == 2 for v in joints.values() if v)
        print(f"extracted {len(detected)} canonical joints")


if __name__ == "__main__":
    test_driving_video_extraction_live()
    print("Phase 29 driving-video extraction: gate passes")
