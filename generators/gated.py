"""Shared gated-provider base for optional AI generators (rig / motion / MCP).

A provider is DISABLED until its capability flag is on (model + isolated env installed).
Asking a disabled provider to act raises NotAvailable — the app degrades, never crashes.
"""

from __future__ import annotations

from server.capabilities import Capabilities


class NotAvailable(RuntimeError):
    pass


class GatedProvider:
    cap_path = ""   # capabilities dotted path, e.g. "autoRig.unirig"
    name = ""

    def __init__(self, caps: Capabilities | None = None):
        self.caps = caps or Capabilities()

    @property
    def available(self) -> bool:
        return self.caps.enabled(self.cap_path)

    def require(self) -> None:
        # Uses self.available so subclasses that also check for an installed env/model win.
        if not self.available:
            raise NotAvailable(
                f"{self.name} disabled — enable capabilities.{self.cap_path} after "
                "installing the model in an isolated environment")
