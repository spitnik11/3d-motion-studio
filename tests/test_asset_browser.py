"""Phase 30 gate: Asset Browser groups assets by category and never surfaces raw
filesystem paths as the main UX (paths live only under per-asset details).

Run: python tests/test_asset_browser.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient  # noqa: E402
import server.api.app as appmod  # noqa: E402
from server.registry.registry import AssetRegistry  # noqa: E402


def test_phase30_asset_browser():
    reg = AssetRegistry(":memory:")
    reg.register("CharacterAsset", "Aiko", creator="me", license="VRoid", format="vrm",
                 localPath="C:/secret/path/aiko.vrm")
    reg.register("PoseAsset", "Wave")
    reg.register("StyleProfile", "Illustrious Base", localPath="C:/models/ill.safetensors")
    appmod._registry = reg  # swap in the test registry

    client = TestClient(appmod.app)
    r = client.get("/api/assets")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 3
    cats = body["categories"]
    assert "Characters" in cats and "Poses" in cats and "Styles" in cats

    # No raw path on the card surface — only inside `details`.
    card = cats["Characters"][0]
    assert "localPath" not in card, "raw path leaked to card surface"
    assert card["name"] == "Aiko" and card["kind"] == "CharacterAsset"
    assert card["details"]["localPath"].endswith("aiko.vrm")

    # UI page renders and drives itself from /api/assets (no server-side paths in markup).
    html = client.get("/")
    assert html.status_code == 200
    assert "3D Motion Studio" in html.text
    assert "C:/secret/path" not in html.text, "UI markup must not embed asset paths"


if __name__ == "__main__":
    test_phase30_asset_browser()
    print("Phase 30 asset browser: gate passes")
