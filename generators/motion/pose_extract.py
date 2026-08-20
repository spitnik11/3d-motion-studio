"""Driving-video pose extraction — Phase 29 (runs in the driving-video env).

video/image → mediapipe pose → 2D canonical joints per frame. Keeps ONLY the
keypoints (movement/timing/pose); source identity and background are discarded.

Invoke with the driving-video env's python:
    python pose_extract.py <input.(mp4|png|jpg)> <out_motion.json> [--stride N]
Output JSON: {"fps": f, "frames": [{"frame": i, "joints": {canonical: [x,y]|null}}]}
"""

import json
import sys

import cv2
import mediapipe as mp

LM = mp.solutions.pose.PoseLandmark

# mediapipe landmark → canonical joint (matches SemanticRig canonical names).
CANON = {
    "head": LM.NOSE,
    "shoulder.left": LM.LEFT_SHOULDER, "arm.left.lower": LM.LEFT_ELBOW, "hand.left": LM.LEFT_WRIST,
    "shoulder.right": LM.RIGHT_SHOULDER, "arm.right.lower": LM.RIGHT_ELBOW, "hand.right": LM.RIGHT_WRIST,
    "leg.left.upper": LM.LEFT_HIP, "leg.left.lower": LM.LEFT_KNEE, "foot.left": LM.LEFT_ANKLE,
    "leg.right.upper": LM.RIGHT_HIP, "leg.right.lower": LM.RIGHT_KNEE, "foot.right": LM.RIGHT_ANKLE,
}


def _joints(landmarks):
    out = {}
    for canonical, idx in CANON.items():
        lm = landmarks[idx.value]
        out[canonical] = [round(lm.x, 5), round(lm.y, 5)] if lm.visibility > 0.3 else None
    # neck = midpoint of shoulders when both present
    ls, rs = out["shoulder.left"], out["shoulder.right"]
    out["spine.upper"] = [round((ls[0] + rs[0]) / 2, 5), round((ls[1] + rs[1]) / 2, 5)] if ls and rs else None
    # pelvis = midpoint of hips
    lh, rh = out["leg.left.upper"], out["leg.right.upper"]
    out["pelvis"] = [round((lh[0] + rh[0]) / 2, 5), round((lh[1] + rh[1]) / 2, 5)] if lh and rh else None
    return out


def extract(in_path: str, out_path: str, stride: int = 1) -> dict:
    pose = mp.solutions.pose.Pose(static_image_mode=in_path.lower().endswith((".png", ".jpg", ".jpeg")))
    frames = []
    if in_path.lower().endswith((".png", ".jpg", ".jpeg")):
        img = cv2.imread(in_path)
        res = pose.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        if res.pose_landmarks:
            frames.append({"frame": 1, "joints": _joints(res.pose_landmarks.landmark)})
        fps = 1.0
    else:
        cap = cv2.VideoCapture(in_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        i = 0
        while True:
            ok, img = cap.read()
            if not ok:
                break
            if i % stride == 0:
                res = pose.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                if res.pose_landmarks:
                    frames.append({"frame": i + 1, "joints": _joints(res.pose_landmarks.landmark)})
            i += 1
        cap.release()
    pose.close()
    data = {"fps": fps, "frames": frames}
    with open(out_path, "w") as f:
        json.dump(data, f)
    return data


if __name__ == "__main__":
    stride = 1
    if "--stride" in sys.argv:
        stride = int(sys.argv[sys.argv.index("--stride") + 1])
    result = extract(sys.argv[1], sys.argv[2], stride)
    print(f"extracted {len(result['frames'])} pose frames")
