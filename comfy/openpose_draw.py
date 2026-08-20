"""Draw an OpenPose (COCO-18) skeleton PNG from a PoseBundle pose.json.

The control-pass renderer already projected canonical joints to 2D. Here we map the
canonical skeleton to the 18 OpenPose body keypoints and render the standard
colored-limb image that the openpose SDXL ControlNet expects. Pillow only.
"""

from __future__ import annotations

from PIL import Image, ImageDraw

# COCO-18 order used by the OpenPose ControlNet.
COCO = ["nose", "neck", "Rsho", "Relb", "Rwri", "Lsho", "Lelb", "Lwri",
        "Rhip", "Rknee", "Rank", "Lhip", "Lknee", "Lank", "Reye", "Leye", "Rear", "Lear"]

# canonical → COCO keypoint (endpoints use bone .head projections in pose.json).
CANON_TO_COCO = {
    "head": "nose", "spine.upper": "neck",
    "shoulder.right": "Rsho", "arm.right.lower": "Relb", "hand.right": "Rwri",
    "shoulder.left": "Lsho", "arm.left.lower": "Lelb", "hand.left": "Lwri",
    "leg.right.upper": "Rhip", "leg.right.lower": "Rknee", "foot.right": "Rank",
    "leg.left.upper": "Lhip", "leg.left.lower": "Lknee", "foot.left": "Lank",
}

# Standard OpenPose limb sequence + colors (RGB).
LIMBS = [
    (1, 2, (255, 0, 0)), (2, 3, (255, 85, 0)), (3, 4, (255, 170, 0)),
    (1, 5, (255, 255, 0)), (5, 6, (170, 255, 0)), (6, 7, (85, 255, 0)),
    (1, 8, (0, 255, 0)), (8, 9, (0, 255, 85)), (9, 10, (0, 255, 170)),
    (1, 11, (0, 255, 255)), (11, 12, (0, 170, 255)), (12, 13, (0, 85, 255)),
    (1, 0, (255, 0, 85)),
]
POINT_COLORS = [
    (255, 0, 0), (255, 85, 0), (255, 170, 0), (255, 255, 0), (170, 255, 0),
    (85, 255, 0), (0, 255, 0), (0, 255, 85), (0, 255, 170), (0, 255, 255),
    (0, 170, 255), (0, 85, 255), (0, 0, 255), (85, 0, 255), (170, 0, 255),
    (255, 0, 255), (255, 0, 170), (255, 0, 85),
]


def draw_openpose(pose_json_actors: dict, size: tuple[int, int], out_path: str) -> str:
    """pose_json_actors = {actor: {canonical: [x,y] | None}}. Draws all actors."""
    w, h = size
    img = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(img)

    for joints in pose_json_actors.values():
        pts = {name: None for name in COCO}
        for canonical, coco in CANON_TO_COCO.items():
            xy = joints.get(canonical)
            if xy:
                pts[coco] = (xy[0] * w, xy[1] * h)
        # neck fallback = midpoint of shoulders
        if pts["neck"] is None and pts["Rsho"] and pts["Lsho"]:
            pts["neck"] = ((pts["Rsho"][0] + pts["Lsho"][0]) / 2,
                           (pts["Rsho"][1] + pts["Lsho"][1]) / 2)

        idx = {name: i for i, name in enumerate(COCO)}
        for a, b, color in LIMBS:
            pa, pb = pts[COCO[a]], pts[COCO[b]]
            if pa and pb:
                d.line([pa, pb], fill=color, width=max(2, w // 128))
        r = max(2, w // 100)
        for name, p in pts.items():
            if p:
                c = POINT_COLORS[idx[name]]
                d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=c)

    img.save(out_path)
    return out_path
