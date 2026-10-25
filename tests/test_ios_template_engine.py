import unittest
import tempfile
import shutil
import zipfile
from pathlib import Path

from web2ipa.template_engine import TemplateEngine

class TestIOSTemplateEngine(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_tmpl_"))

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_generate_xcode_project(self):
        res = TemplateEngine.generate_project(
            target_dir=str(self.test_dir),
            app_name="CyberArcade",
            bundle_id="com.web2ipa.cyberarcade",
            version_name="1.0.0",
            version_code=1,
            remote_url="https://cyberarcade.example.com",
            is_fullscreen=True,
            theme_color="#0a84ff",
            extra_permissions=["NSCameraUsageDescription", "NSLocationWhenInUseUsageDescription"]
        )

        self.assertTrue(res["success"])
        app_dir = Path(res["app_folder"])
        
        # Verify Swift files
        self.assertTrue((app_dir / "AppDelegate.swift").exists())
        self.assertTrue((app_dir / "SceneDelegate.swift").exists())
        self.assertTrue((app_dir / "WebViewController.swift").exists())
        self.assertTrue((app_dir / "Info.plist").exists())
        self.assertTrue((app_dir / "offline.html").exists())

        # Verify Info.plist contains privacy strings
        info_plist_content = (app_dir / "Info.plist").read_text(encoding="utf-8")
        self.assertIn("NSCameraUsageDescription", info_plist_content)
        self.assertIn("NSLocationWhenInUseUsageDescription", info_plist_content)
        self.assertIn("com.web2ipa.cyberarcade", info_plist_content)

        # Verify project.pbxproj
        xcodeproj = Path(res["xcodeproj_path"])
        self.assertTrue((xcodeproj / "project.pbxproj").exists())
        pbx_content = (xcodeproj / "project.pbxproj").read_text(encoding="utf-8")
        self.assertIn("PBXProject", pbx_content)
        self.assertIn("CyberArcade", pbx_content)

        # Verify project zipping
        out_zip = self.test_dir / "CyberArcade.zip"
        TemplateEngine.zip_project(self.test_dir, out_zip)
        self.assertTrue(out_zip.exists())
        with zipfile.ZipFile(out_zip, 'r') as zf:
            names = zf.namelist()
            self.assertTrue(any("project.pbxproj" in n for n in names))

    def test_ios_offline_caching_and_bridge(self):
        """Verify iOS offline caching, bridge reload, and GeminiAdvisor offline resilience."""
        from web2ipa.ai_advisor import GeminiAdvisor
        from unittest.mock import patch

        # 1. GeminiAdvisor offline detection & heuristics
        self.assertIsInstance(GeminiAdvisor.is_online(), bool)
        with patch.object(GeminiAdvisor, "is_online", return_value=False):
            self.assertFalse(GeminiAdvisor.is_available())
            models = GeminiAdvisor.discover_available_models()
            self.assertTrue(len(models) > 0)

            # Heuristic offline analysis
            opt = GeminiAdvisor.analyze_and_optimize_code("<h1>Test</h1>", "iOSApp")
            self.assertTrue(opt.get("success"))
            self.assertEqual(opt.get("model_used"), "offline-engine")

            # Heuristic offline metadata
            meta = GeminiAdvisor.generate_app_store_metadata("iOSApp")
            self.assertEqual(meta.get("model_used"), "offline-engine")

        # 2. Template inspection for returnCacheDataElseLoad & retry bridge
        res = TemplateEngine.generate_project(
            target_dir=str(self.test_dir / "offline_proj"),
            app_name="OfflineApp",
            bundle_id="com.web2ipa.offlineapp",
            version_name="1.0.0",
            version_code=1,
            remote_url="https://offline-remote.example.com",
            is_fullscreen=False,
            theme_color="#000000"
        )
        app_dir = Path(res["app_folder"])
        wvc_content = (app_dir / "WebViewController.swift").read_text(encoding="utf-8")
        self.assertIn(".returnCacheDataElseLoad", wvc_content)
        self.assertIn('case "retry", "refresh":', wvc_content)
        self.assertIn("loadContent()", wvc_content)

        offline_html = (app_dir / "offline.html").read_text(encoding="utf-8")
        self.assertIn('window.webkit.messageHandlers.iOSApp.postMessage({action: "retry"})', offline_html)

if __name__ == "__main__":
    unittest.main()
