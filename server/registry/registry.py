"""AssetRegistry — Phase 2.

Persistent metadata store for every asset the studio knows about. Backed by
stdlib sqlite3 so metadata survives a restart byte-for-byte (the Phase 2 gate).

One table, keyed by `kind` — the nine entity types share the same provenance
shape, so nine classes would be nine copies of the same fields. Type-specific
extras go in `payload` (arbitrary JSON).

Permission rule (non-negotiable): unknown permission is UNKNOWN, never ALLOWED.
The four *Allowed fields default to None and are NEVER coerced to True.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

# The nine registry entities (plan Phase 2).
KINDS = {
    "CharacterAsset",
    "SceneAsset",
    "PropAsset",
    "MotionAsset",
    "PoseAsset",
    "HandPoseAsset",
    "PairPoseAsset",
    "RigProfile",
    "StyleProfile",
}

# Tri-state permission fields: True=YES, False=NO, None=UNKNOWN.
PERMISSION_FIELDS = (
    "commercialAllowed",
    "modificationAllowed",
    "redistributionAllowed",
    "matureUseAllowed",
)

# Full provenance block stored for every asset. None = unknown.
_PROVENANCE_DEFAULTS = {
    "creator": "",
    "source": "",
    "sourceUrl": "",
    "downloadedAt": "",
    "sha256": "",
    "license": "",
    "licenseSnapshot": "",
    "commercialAllowed": None,
    "modificationAllowed": None,
    "redistributionAllowed": None,
    "matureUseAllowed": None,
    "format": "",
    "localPath": "",
}

_DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "registry" / "assets.db"


def permission_label(value) -> str:
    """Tri-state → display string. None (or anything not explicitly True/False) is UNKNOWN."""
    if value is True:
        return "YES"
    if value is False:
        return "NO"
    return "UNKNOWN"


def _sha256(path: str) -> str:
    p = Path(path)
    if not path or not p.is_file():
        return ""
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class AssetRegistry:
    def __init__(self, db_path: str | Path = _DEFAULT_DB):
        self.db_path = str(db_path)
        if db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False: the API serves reads from a threadpool. SQLite still
        # serializes access and this tool is single-writer, so this is safe.
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS assets (
                id     TEXT PRIMARY KEY,
                kind   TEXT NOT NULL,
                name   TEXT NOT NULL,
                sha256 TEXT,
                data   TEXT NOT NULL
            )"""
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def register(self, kind: str, name: str, *, payload: dict | None = None, **provenance) -> dict:
        """Add an asset. `provenance` overrides the default block (unknown perms stay None).

        Computes sha256 from localPath when the file exists and no hash was supplied.
        Returns the stored record.
        """
        if kind not in KINDS:
            raise ValueError(f"unknown kind {kind!r}; expected one of {sorted(KINDS)}")
        unexpected = set(provenance) - set(_PROVENANCE_DEFAULTS)
        if unexpected:
            raise ValueError(f"unexpected provenance fields: {sorted(unexpected)}")

        record = {"id": str(uuid.uuid4()), "kind": kind, "name": name}
        record.update(_PROVENANCE_DEFAULTS)
        record.update(provenance)
        record["payload"] = payload or {}

        if not record["downloadedAt"]:
            record["downloadedAt"] = datetime.now(timezone.utc).isoformat()
        if not record["sha256"] and record["localPath"]:
            record["sha256"] = _sha256(record["localPath"])

        self._conn.execute(
            "INSERT INTO assets (id, kind, name, sha256, data) VALUES (?, ?, ?, ?, ?)",
            (record["id"], kind, name, record["sha256"], json.dumps(record)),
        )
        self._conn.commit()
        return record

    def get(self, asset_id: str) -> dict | None:
        row = self._conn.execute("SELECT data FROM assets WHERE id = ?", (asset_id,)).fetchone()
        return json.loads(row["data"]) if row else None

    def all(self, kind: str | None = None) -> list[dict]:
        if kind is not None:
            rows = self._conn.execute(
                "SELECT data FROM assets WHERE kind = ? ORDER BY name", (kind,)
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT data FROM assets ORDER BY kind, name").fetchall()
        return [json.loads(r["data"]) for r in rows]

    def delete(self, asset_id: str) -> bool:
        cur = self._conn.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
        self._conn.commit()
        return cur.rowcount > 0
