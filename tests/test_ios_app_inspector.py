import unittest
import tempfile
import shutil
from pathlib import Path

from web2ipa.app_inspector import iOSAppInspector

class TestIOSAppInspector(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_inspector_"))

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_inspect_directory_with_html(self):
        index_html = self.test_dir / "index.html"
        index_html.write_text("""<!DOCTYPE html>
<html>
<head>
    <title>Quantum Arcade</title>
    <meta name="theme-color" content="#0a84ff">
    <meta name="apple-mobile-web-app-title" content="Quantum">
</head>
<body>
    <script>
        navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        navigator.geolocation.getCurrentPosition(() => {});
    </script>
</body>
</html>
""", encoding="utf-8")

        bp = iOSAppInspector.inspect_directory(self.test_dir)
        self.assertEqual(bp["app_name"], "Quantum")
        self.assertEqual(bp["theme_color"], "#0a84ff")
        self.assertIn("com.web2ipa.quantum", bp["bundle_id"])

        perms = bp["ios_permissions"]
        self.assertIn("NSCameraUsageDescription", perms)
        self.assertIn("NSMicrophoneUsageDescription", perms)
        self.assertIn("NSLocationWhenInUseUsageDescription", perms)

    def test_inspect_package_json(self):
        pkg_json = self.test_dir / "package.json"
        pkg_json.write_text("""{
  "name": "stellar-browser",
  "version": "2.4.1"
}""", encoding="utf-8")

        bp = iOSAppInspector.inspect_directory(self.test_dir)
        self.assertIn("Stellar", bp["app_name"])
        self.assertEqual(bp["version_name"], "2.4.1")

    def test_autodetect_apple_touch_icon_link(self):
        assets_dir = self.test_dir / "assets"
        assets_dir.mkdir()
        icon_file = assets_dir / "custom-touch-icon.png"
        icon_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa")

        index_html = self.test_dir / "index.html"
        index_html.write_text("""<!DOCTYPE html>
<html>
<head>
    <title>Touch Icon App</title>
    <link rel="apple-touch-icon" href="assets/custom-touch-icon.png">
</head>
<body><h1>Hello</h1></body>
</html>""", encoding="utf-8")

        bp = iOSAppInspector.inspect_directory(self.test_dir)
        self.assertIsNotNone(bp.get("icon_path"))
        self.assertIn("custom-touch-icon", bp.get("detection_sources", {}).get("icon", ""))

    def test_autodetect_logo_in_subfolder(self):
        img_dir = self.test_dir / "public" / "images"
        img_dir.mkdir(parents=True)
        logo_file = img_dir / "app_logo.png"
        logo_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa")

        bp = iOSAppInspector.inspect_directory(self.test_dir)
        self.assertIsNotNone(bp.get("icon_path"))
        self.assertTrue(Path(bp["icon_path"]).exists())
        self.assertIn("app_logo.png", bp.get("detection_sources", {}).get("icon", ""))

    def test_autodetect_manifest_icon(self):
        manifest = self.test_dir / "manifest.json"
        icons_dir = self.test_dir / "icons"
        icons_dir.mkdir()
        manifest_ico = icons_dir / "icon-512.png"
        manifest_ico.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa")

        manifest.write_text("""{
  "name": "Manifest App",
  "icons": [
    { "src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}""", encoding="utf-8")

        bp = iOSAppInspector.inspect_directory(self.test_dir)
        self.assertIsNotNone(bp.get("icon_path"))
        self.assertTrue(Path(bp["icon_path"]).exists())

if __name__ == "__main__":
    unittest.main()
