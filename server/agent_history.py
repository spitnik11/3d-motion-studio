"""Agent snapshot / undo — Phase 25.

Every agent action snapshots the session .blend before applying, so a single undo
restores the previous state. Agent edits go through apply_pose_commands-style command
lists, which already skip locked bones — so agent changes never overwrite pose locks.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from server.blender_bridge import BlenderBridge


class AgentHistory:
    def __init__(self, session_blend: str, bridge: BlenderBridge | None = None):
        self.blend = str(session_blend)
        self.bridge = bridge or BlenderBridge()
        self._snaps_dir = Path(tempfile.mkdtemp(prefix="agent_hist_"))
        self.stack: list[dict] = []

    def _snapshot(self, tag: str) -> str:
        p = self._snaps_dir / f"{len(self.stack)}_{tag}.blend"
        shutil.copy2(self.blend, p)
        return str(p)

    def apply(self, commands: list[dict], *, label: str, actor: str = "agent") -> list[dict]:
        """Snapshot the current state, then apply commands to the session blend."""
        before = self._snapshot("before")
        results = self.bridge.run(commands, blend_in=self.blend, blend_out=self.blend)
        self.stack.append({"label": label, "actor": actor, "before": before,
                           "commands": commands,
                           "warnings": [r for r in results if not r["ok"]]})
        return results

    def undo(self) -> dict | None:
        """Restore the state prior to the last agent action."""
        if not self.stack:
            return None
        rec = self.stack.pop()
        shutil.copy2(rec["before"], self.blend)
        return rec

    def log(self) -> list[dict]:
        return [{"label": r["label"], "actor": r["actor"],
                 "warnings": len(r["warnings"])} for r in self.stack]
