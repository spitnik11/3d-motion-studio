"""BlenderBridge (venv side) — Phase 3.

The public, validated command surface. Launches Blender headless, runs a batch of
commands through blender/bridge/bridge_ops.py, and returns their results. Callers
never send raw Python — only op dicts.

    bridge = BlenderBridge()
    results = bridge.run([{"op": "health"}], blend_out="scene.blend")
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_OPS_SCRIPT = _ROOT / "blender" / "bridge" / "bridge_ops.py"
_CONFIG = _ROOT / "config" / "default.json"


class BridgeError(RuntimeError):
    pass


class BlenderBridge:
    def __init__(self, blender_exe: str | None = None, timeout: int = 300):
        self.timeout = timeout
        self.blender_exe = blender_exe or json.loads(_CONFIG.read_text())["blender"]["executable"]
        if not self.blender_exe or not Path(self.blender_exe).is_file():
            raise BridgeError(
                f"Blender executable not found: {self.blender_exe!r}. "
                "Set config/default.json → blender.executable."
            )

    def run(self, commands: list[dict], *, blend_in: str | None = None,
            blend_out: str | None = None) -> list[dict]:
        """Execute commands in one headless Blender launch. Returns per-command results.

        blend_in: open this .blend first (else empty factory scene).
        blend_out: appended as a final saveProject so the batch persists.
        """
        cmds = list(commands)
        if blend_out:
            cmds.append({"op": "saveProject", "path": blend_out})

        with tempfile.TemporaryDirectory() as tmp:
            cmd_file = Path(tmp) / "commands.json"
            res_file = Path(tmp) / "result.json"
            cmd_file.write_text(json.dumps(cmds), encoding="utf-8")

            argv = self.build_argv(blend_in, str(cmd_file), str(res_file))

            proc = subprocess.run(argv, capture_output=True, text=True, timeout=self.timeout)
            if not res_file.exists():
                raise BridgeError(
                    f"Blender produced no result (exit {proc.returncode}).\n"
                    f"stderr tail:\n{proc.stderr[-2000:]}"
                )
            return json.loads(res_file.read_text(encoding="utf-8"))

    def build_argv(self, blend_in, cmd_file: str, res_file: str) -> list[str]:
        # --disable-autoexec: never auto-run Python embedded in a loaded .blend
        # (external blends are untrusted; our own bridge_ops via --python still runs).
        argv = [self.blender_exe, "--background", "--disable-autoexec"]
        if blend_in:
            argv.append(blend_in)
        argv += ["--python", str(_OPS_SCRIPT), "--", cmd_file, res_file]
        return argv

    def health(self) -> dict:
        return self.run([{"op": "health"}])[0]
