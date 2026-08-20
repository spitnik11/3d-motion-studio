"""Phase 2 gate: import an asset, restart (reopen the DB), recover identical metadata.

Run: python tests/test_registry.py   (or: python -m pytest tests/test_registry.py)
Stdlib only, no framework needed.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.registry.registry import AssetRegistry, permission_label  # noqa: E402


def test_gate_restart_recovers_identical_metadata():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "assets.db"

        # Import against one instance.
        reg = AssetRegistry(db)
        stored = reg.register(
            "CharacterAsset",
            "VRoid Test Girl",
            creator="me",
            source="VRoid Studio",
            license="VRoid custom",
            format="vrm",
            # deliberately leave commercial/redistribution unknown
            modificationAllowed=True,
            payload={"rig": "vrm", "heightCm": 165},
        )
        reg.close()  # simulate app shutdown

        # Restart: brand-new instance on the same file.
        reg2 = AssetRegistry(db)
        recovered = reg2.get(stored["id"])
        assert recovered == stored, "metadata not byte-identical after restart"
        assert len(reg2.all("CharacterAsset")) == 1
        reg2.close()


def test_unknown_permission_is_never_allowed():
    reg = AssetRegistry(":memory:")
    a = reg.register("SceneAsset", "Downloaded Ring", source="somewhere")
    # unspecified perms must be UNKNOWN, not allowed
    for field in ("commercialAllowed", "redistributionAllowed", "matureUseAllowed"):
        assert a[field] is None, f"{field} should default to None (UNKNOWN)"
        assert permission_label(a[field]) == "UNKNOWN"
    assert permission_label(True) == "YES"
    assert permission_label(False) == "NO"
    reg.close()


def test_rejects_bad_kind():
    reg = AssetRegistry(":memory:")
    try:
        reg.register("NotAThing", "x")
        assert False, "should have rejected unknown kind"
    except ValueError:
        pass
    reg.close()


if __name__ == "__main__":
    test_gate_restart_recovers_identical_metadata()
    test_unknown_permission_is_never_allowed()
    test_rejects_bad_kind()
    print("Phase 2 registry: all checks pass")
