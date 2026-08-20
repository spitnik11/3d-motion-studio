"""Gates for Phases 26, 27, 32. Pure logic + one Blender undo round-trip.

 26 agent pose assist: Accept/Reject/Revert/Edit
 27 agent animation assist works around locked edits
 32 agent summarizes license; only a human approves

Run: python tests/test_agent_assist_license.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.blender_bridge import BlenderBridge  # noqa: E402
from server.agent_history import AgentHistory  # noqa: E402
from server.agent_assist import propose_pose, propose_breakdown, retime  # noqa: E402
from server.posing import apply_pose_commands  # noqa: E402
from server.license_gate import license_summary, render_license_block, ImportApproval  # noqa: E402


def test_phase26_pose_assist_accept_reject_revert():
    bridge = BlenderBridge()
    with tempfile.TemporaryDirectory() as tmp:
        blend = str(Path(tmp) / "s.blend")
        assert all(x["ok"] for x in bridge.run(
            [{"op": "newScene"}, {"op": "createHumanoidFixture", "name": "A"}], blend_out=blend))
        hist = AgentHistory(blend, bridge)

        def leg():
            return bridge.run([{"op": "getBoneRotation", "armature": "A", "bone": "leg.left.upper"}],
                              blend_in=blend)[0]["euler"][2]

        # Propose → Reject (nothing applied).
        proposal = propose_pose("make the stance wider")
        assert "leg.left.upper" in proposal["bones"]
        assert abs(leg()) < 1e-6  # rejected: not applied

        # Edit the proposal, then Accept (applied).
        proposal["bones"]["leg.left.upper"]["euler"][2] = 0.5  # user edit
        hist.apply(apply_pose_commands(proposal, "A", "canonical"), label="widen")
        assert abs(leg() - 0.5) < 1e-3

        # Revert.
        hist.undo()
        assert abs(leg()) < 1e-6, "revert did not undo the accepted proposal"

    # locked bones excluded from a proposal
    p = propose_pose("make the stance wider", locks={"leg.left.upper"})
    assert "leg.left.upper" not in p["bones"] and "leg.right.upper" in p["bones"]


def test_phase27_animation_assist_respects_locks():
    a = {"bones": {"arm.left.upper": {"euler": [0, 0, 0]}, "hand.right": {"euler": [0, 0, 0]}}}
    b = {"bones": {"arm.left.upper": {"euler": [1.0, 0, 0]}, "hand.right": {"euler": [1.0, 0, 0]}}}
    bd = propose_breakdown(a, b, 0.5, locks={"hand.right"})
    assert "hand.right" not in bd["bones"], "breakdown overrode a locked bone"
    assert abs(bd["bones"]["arm.left.upper"]["euler"][0] - 0.5) < 1e-9
    # retime stretches timing deterministically
    rt = retime({1: a, 5: b}, 2.0)
    assert set(rt) == {2, 10}


def test_phase32_license_summary_and_human_approval():
    prov = {"creator": "SomeArtist", "source": "VRoid Hub", "license": "VRoid custom",
            "modificationAllowed": True}  # others unknown
    s = license_summary(prov)
    assert s["permissions"]["modificationAllowed"] == "YES"
    assert s["permissions"]["commercialAllowed"] == "UNKNOWN"  # never assumed allowed
    assert "Approve Import" in render_license_block(prov)

    gate = ImportApproval(prov)
    _ = gate.agent_summary()  # agents may summarize
    try:
        gate.approve(by="agent")
        assert False, "agent must not approve"
    except PermissionError:
        pass
    gate.approve(by="gabriel")
    assert gate.approved and gate.approved_by == "gabriel"


if __name__ == "__main__":
    test_phase26_pose_assist_accept_reject_revert()
    test_phase27_animation_assist_respects_locks()
    test_phase32_license_summary_and_human_approval()
    print("Phases 26/27/32 agent assist + license gate: gates pass")
