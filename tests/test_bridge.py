"""Phase 3 gate: launch Blender, create scene, create object, move it, save,
reopen, verify the transform survived. Real headless Blender — no mocks.

Run: python tests/test_bridge.py   (needs Blender installed + config path set)
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.blender_bridge import BlenderBridge  # noqa: E402


def test_gate_roundtrip_transform():
    bridge = BlenderBridge()
    with tempfile.TemporaryDirectory() as tmp:
        blend = str(Path(tmp) / "scene.blend")

        # Launch → new scene → create object → move it → save.
        r1 = bridge.run(
            [
                {"op": "newScene"},
                {"op": "createObject", "kind": "cube", "name": "Marker", "location": [0, 0, 0]},
                {"op": "setTransform", "name": "Marker", "location": [1.5, -2.0, 3.25]},
            ],
            blend_out=blend,
        )
        assert all(r["ok"] for r in r1), r1

        # Reopen the saved file in a fresh Blender launch → verify transform.
        r2 = bridge.run(
            [
                {"op": "listObjects"},
                {"op": "getTransform", "name": "Marker"},
            ],
            blend_in=blend,
        )
        assert all(r["ok"] for r in r2), r2
        assert "Marker" in r2[0]["objects"], r2[0]
        loc = r2[1]["location"]
        assert loc == [1.5, -2.0, 3.25], f"transform not preserved: {loc}"


def test_unknown_op_reports_not_crashes():
    bridge = BlenderBridge()
    r = bridge.run([{"op": "definitelyNotAnOp"}])
    assert r[0]["ok"] is False and "unknown op" in r[0]["error"]


if __name__ == "__main__":
    test_gate_roundtrip_transform()
    test_unknown_op_reports_not_crashes()
    print("Phase 3 Blender Bridge: gate passes")
