"""Capabilities & config — the graceful-degradation backbone (Phases 21 & 35).

Every optional AI feature is a capability flag in config. A missing/disabled provider
must DISABLE its feature, never crash the app. Manual posing never depends on any of
these flags.
"""

from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT = _ROOT / "config" / "default.json"
_LOCAL = _ROOT / "config" / "local.json"


def load_config() -> dict:
    cfg = json.loads(_DEFAULT.read_text())
    if _LOCAL.is_file():
        _deep_update(cfg, json.loads(_LOCAL.read_text()))
    return cfg


def _deep_update(a: dict, b: dict) -> dict:
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            _deep_update(a[k], v)
        else:
            a[k] = v
    return a


class Capabilities:
    """Read-only view of config → capabilities.*, with dotted lookups."""

    def __init__(self, config: dict | None = None):
        self.config = config or load_config()
        self.caps = self.config.get("capabilities", {})

    def enabled(self, dotted: str) -> bool:
        node = self.caps
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return False
            node = node[part]
        return bool(node)

    def require(self, dotted: str) -> None:
        if not self.enabled(dotted):
            raise CapabilityDisabled(dotted)

    def flat(self) -> dict:
        out = {}

        def walk(prefix, node):
            for k, v in node.items():
                key = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    walk(key, v)
                else:
                    out[key] = bool(v)
        walk("", self.caps)
        return out


class CapabilityDisabled(RuntimeError):
    def __init__(self, cap: str):
        super().__init__(f"capability disabled: {cap}")
        self.capability = cap
