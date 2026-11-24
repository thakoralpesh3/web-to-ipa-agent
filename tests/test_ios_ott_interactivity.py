import unittest
import tempfile
import shutil
from pathlib import Path

from web2ipa.template_engine import TemplateEngine


class TestIOSOTTInteractivity(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="web2ipa_ott_test_"))

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_ios_ott_interactivity_in_web_view_controller(self):
        """Verify WebViewController includes Hotstar/Netflix-like gestures, glassmorphic HUD, and video controls."""
        project_dir = self.test_dir / "ios_ott_proj"
        res = TemplateEngine.generate_project(
            target_dir=str(project_dir),
            app_name="StreamVisionIOS",
            bundle_id="com.example.streamvision",
            remote_url="https://streaming.example.com",
            is_fullscreen=True,
            theme_color="#0b0f19"
        )
        self.assertTrue(res.get("success"))

        wvc_file = project_dir / "StreamVisionIOS/WebViewController.swift"
        self.assertTrue(wvc_file.exists())
        src = wvc_file.read_text(encoding="utf-8")

        # 1. OTT UI Components & Glassmorphism Blur
        self.assertIn("ottBottomNav", src)
        self.assertIn("ottControlsContainer", src)
        self.assertIn("ottCenterHud", src)
        self.assertIn("systemUltraThinMaterialDark", src)

        # 2. Touch Gestures (Double Tap 10s seek, Pan Brightness/Volume, Single Tap toggle)
        self.assertIn("setupGestures()", src)
        self.assertIn("handleDoubleTap", src)
        self.assertIn("handlePanGesture", src)
        self.assertIn("handleSingleTap", src)
        self.assertIn("gobackward.10", src)
        self.assertIn("goforward.10", src)
        self.assertIn("UIScreen.main.brightness", src)

        # 3. Floating Player Controls & Video Bridge
        self.assertIn("handleOttPlayPause", src)
        self.assertIn("handleOttSpeed", src)
        self.assertIn("handleOttPip", src)
        self.assertIn("handleOttLock", src)
        self.assertIn("webkitSetPresentationMode", src)

        # 4. Injected OTT Video JavaScript
        self.assertIn("window.__ottSeek", src)
        self.assertIn("window.__ottSetSpeed", src)
        self.assertIn("window.__ottTogglePlay", src)
        self.assertIn("window.OTTPlayer", src)

        # 5. WKScriptMessageHandler Actions
        self.assertIn('case "triggerPiP":', src)
        self.assertIn('case "seekRelative":', src)
        self.assertIn('case "setPlaybackSpeed":', src)
        self.assertIn('case "toggleScreenLock":', src)
        self.assertIn('case "setOttNavVisible":', src)


if __name__ == "__main__":
    unittest.main()
