import unittest
import tempfile
import shutil
from pathlib import Path

from web2ipa.template_engine import TemplateEngine
from web2ipa.self_healer import iOSSelfHealer


class TestIOSDownloadBridge(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="web2ipa_dl_test_"))

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_ios_download_bridge_in_web_view_controller(self):
        """Verify WebViewController contains downloadBridgeJS, saveFile, and navigation response interceptor."""
        project_dir = self.test_dir / "ios_dl_proj"
        res = TemplateEngine.generate_project(
            target_dir=str(project_dir),
            app_name="DataVaultIOS",
            bundle_id="com.example.datavault",
            remote_url="https://datavault.example.com",
            is_fullscreen=False,
            theme_color="#0f172a"
        )
        self.assertTrue(res.get("success"))

        wvc_file = project_dir / "DataVaultIOS/WebViewController.swift"
        self.assertTrue(wvc_file.exists())
        src = wvc_file.read_text(encoding="utf-8")

        # 1. Verify downloadBridgeJS injected in WKUserScript
        self.assertIn("downloadBridgeJS", src)
        self.assertIn("window.__web2ipa_download_interceptor", src)
        self.assertIn(".sqlite", src)

        # 2. Verify saveFile action in userContentController
        self.assertIn('case "saveFile":', src)
        self.assertIn("Data(base64Encoded: cleanBase64)", src)
        self.assertIn("SQLite format 3", src)
        self.assertIn("UIActivityViewController", src)

        # 3. Verify downloadUrl and navigation response interceptor
        self.assertIn('case "downloadUrl":', src)
        self.assertIn("decidePolicyFor navigationResponse", src)
        self.assertIn("downloadAndShare", src)

    def test_self_healer_injects_download_bridge(self):
        """Verify iOSSelfHealer injects universal download interceptor into HTML."""
        sample_html = "<html><head><title>Test</title></head><body><button onclick='downloadDb()'>Export</button></body></html>"
        html_file = self.test_dir / "index.html"
        html_file.write_text(sample_html, encoding="utf-8")

        res = iOSSelfHealer.diagnose_and_repair(self.test_dir, app_name="TestApp")
        self.assertTrue(res.get("repaired"))
        healed = html_file.read_text(encoding="utf-8")
        self.assertIn("ios-download-interceptor", healed)
        self.assertIn("saveFile", healed)
        self.assertIn(".sqlite", healed)


if __name__ == "__main__":
    unittest.main()
