"""
Validation tests for Microsoft Edge extension configuration and assets.
"""
import json
from pathlib import Path

EXT_DIR = Path(__file__).resolve().parent.parent / "edge_extension"


def test_manifest_is_valid():
    manifest_path = EXT_DIR / "manifest.json"
    assert manifest_path.exists()

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["manifest_version"] == 3
    assert "name" in data
    assert "version" in data
    assert "declarativeNetRequest" in data["permissions"]
    assert "declarative_net_request" in data
    assert any("youtube.com" in h for h in data["host_permissions"])
    assert any("instagram.com" in h for h in data["host_permissions"])
    assert len(data["content_scripts"]) == 2
    assert "icons" in data
    assert "128" in data["icons"]


def test_rules_json_contains_home_and_reels_redirects():
    rules_path = EXT_DIR / "rules.json"
    assert rules_path.exists()

    with open(rules_path, "r", encoding="utf-8") as f:
        rules = json.load(f)

    # Verify Instagram Home redirect rule exists
    home_rules = [r for r in rules if "instagram.com/direct/inbox/" in r.get("action", {}).get("redirect", {}).get("url", "")
                  and "instagram\\.com/?(?:\\?.*)?(?:#.*)?$" in r.get("condition", {}).get("regexFilter", "")]
    assert len(home_rules) == 1, "Instagram Home page redirect rule must be present in rules.json"

    # Verify Instagram Reels redirect rule exists
    reel_rules = [r for r in rules if "instagram.com/direct/inbox/" in r.get("action", {}).get("redirect", {}).get("url", "")
                  and "(?:reel|reels)" in r.get("condition", {}).get("regexFilter", "")]
    assert len(reel_rules) == 1, "Instagram Reels redirect rule must be present in rules.json"


def test_extension_assets_exist():
    assert (EXT_DIR / "css" / "youtube.css").exists()
    assert (EXT_DIR / "css" / "instagram.css").exists()
    assert (EXT_DIR / "css" / "block_screen.css").exists()
    assert (EXT_DIR / "scripts" / "youtube_blocker.js").exists()
    assert (EXT_DIR / "scripts" / "instagram_blocker.js").exists()
    assert (EXT_DIR / "icons" / "icon16.png").exists()
    assert (EXT_DIR / "icons" / "icon32.png").exists()
    assert (EXT_DIR / "icons" / "icon48.png").exists()
    assert (EXT_DIR / "icons" / "icon128.png").exists()


def test_block_screen_contains_key_elements():
    block_css = (EXT_DIR / "css" / "block_screen.css").read_text(encoding="utf-8")
    assert "#focuslens-block-overlay" in block_css
    assert "z-index: 2147483647" in block_css
    assert ".focuslens-card" in block_css

    yt_script = (EXT_DIR / "scripts" / "youtube_blocker.js").read_text(encoding="utf-8")
    assert "YouTube Short Blocked" in yt_script
    assert "Watch as Standard YouTube Video" in yt_script

    ig_script = (EXT_DIR / "scripts" / "instagram_blocker.js").read_text(encoding="utf-8")
    assert "Instagram Reel Blocked" in ig_script
    assert "Open Direct Messages" in ig_script
    assert "isHomePage" in ig_script
    assert "redirectToInbox" in ig_script
    assert "https://www.instagram.com/direct/inbox/" in ig_script

    ig_css = (EXT_DIR / "css" / "instagram.css").read_text(encoding="utf-8")
    assert 'svg[aria-label="Home"]' in ig_css
