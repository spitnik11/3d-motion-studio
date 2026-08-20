"""Gates for Phases 24, 25, 33.

 24 Agent API exposes only validated semantic primitives (no arbitrary Blender Python)
 25 an agent's bad edit is reverted by one undo; locks are never overwritten
 33 external .blend handling disables auto script execution

Run: python tests/test_agent_api.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient  # noqa: E402
from server.api.app import app, SEMANTIC_VERBS  # noqa: E402
from server.blender_bridge import BlenderBridge  # noqa: E402
from server.agent_history import AgentHistory  # noqa: E402
from server.posing import apply_pose_commands  # noqa: E402


def test_phase24_agent_api_semantic_only():
    client = TestClient(app)

    # diagnostics
    d = client.get("/api/diagnostics")
    assert d.status_code == 200 and d.json()["blender"]["available"] is True

    # create a scene session
    manifest = {"ground": True, "lights": [{"type": "SUN", "name": "Key"}],
                "camera": "medium", "actors": [{"name": "A", "offset": [0, 0, 0]}]}
    r = client.post("/api/scenes", json={"manifest": manifest})
    assert r.status_code == 200, r.text
    sid = r.json()["session"]
    assert "A" in r.json()["objects"]

    # semantic command works
    r2 = client.post("/api/poses/apply",
                     json={"session": sid, "armature": "A", "command": "raise left arm"})
    assert r2.status_code == 200 and r2.json()["applied"] > 0

    # unknown semantic command rejected
    r3 = client.post("/api/poses/apply",
                     json={"session": sid, "armature": "A", "command": "run arbitrary code"})
    assert r3.status_code == 400

    # NO arbitrary-op passthrough: an op-shaped payload doesn't validate.
    r4 = client.post("/api/poses/apply", json={"session": sid, "op": "runPython", "code": "x"})
    assert r4.status_code == 422  # missing required 'armature', extra ignored → invalid
    # there is no exec-style route
    paths = {route.path for route in app.routes}
    assert not any("exec" in p or "python" in p for p in paths)
    assert "raise left arm" in SEMANTIC_VERBS


def test_phase25_snapshot_undo_and_locks():
    bridge = BlenderBridge()
    with tempfile.TemporaryDirectory() as tmp:
        blend = str(Path(tmp) / "session.blend")
        assert all(x["ok"] for x in bridge.run(
            [{"op": "newScene"}, {"op": "createHumanoidFixture", "name": "A"}], blend_out=blend))

        hist = AgentHistory(blend, bridge)
        hist.apply(apply_pose_commands({"bones": {"arm.left.upper": {"euler": [0.4, 0, 0]}}}, "A", "canonical"),
                   label="edit1")
        hist.apply(apply_pose_commands({"bones": {"arm.left.upper": {"euler": [1.0, 0, 0]}}}, "A", "canonical"),
                   label="edit2(bad)")

        def read():
            return bridge.run([{"op": "getBoneRotation", "armature": "A", "bone": "arm.left.upper"}],
                              blend_in=blend)[0]["euler"][0]

        assert abs(read() - 1.0) < 1e-3
        hist.undo()  # revert the bad edit
        assert abs(read() - 0.4) < 1e-3, "undo did not restore previous state"

        # Agent edit must not move a locked bone.
        hist.apply(apply_pose_commands({"bones": {"arm.left.upper": {"euler": [0.9, 0, 0]}}},
                                       "A", "canonical", locks={"arm.left.upper"}),
                   label="locked-edit")
        assert abs(read() - 0.4) < 1e-3, "locked bone was moved by agent"


def test_phase33_disable_autoexec():
    bridge = BlenderBridge()
    argv = bridge.build_argv("scene.blend", "c.json", "r.json")
    assert "--disable-autoexec" in argv, "untrusted blends must not auto-run scripts"
    # functional: appending an external collection still works with autoexec off
    with tempfile.TemporaryDirectory() as tmp:
        ext = str(Path(tmp) / "ext.blend")
        assert all(x["ok"] for x in bridge.run(
            [{"op": "newScene"}, {"op": "createObject", "kind": "cube", "name": "Widget"}],
            blend_out=ext))
        r = bridge.run([{"op": "newScene"}, {"op": "importScene", "path": ext}])
        assert r[1]["ok"] and "Widget" in r[1]["objects"], r


if __name__ == "__main__":
    test_phase24_agent_api_semantic_only()
    test_phase25_snapshot_undo_and_locks()
    test_phase33_disable_autoexec()
    print("Phases 24/25/33 agent API + undo + blend security: gates pass")
