import unittest
import tempfile
import shutil
from pathlib import Path
from PIL import Image

from web2ipa.builder import IPABuilder, OUTPUT_DIR

class TestIOSBuilder(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_builder_"))

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_build_from_directory(self):
        # Create minimal web application
        (self.test_dir / "index.html").write_text("""<!DOCTYPE html>
<html>
<head>
    <title>Galactic Arcade</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="background:#111;">
    <h1>Welcome to Galactic Arcade</h1>
</body>
</html>
""", encoding="utf-8")

        # Create dummy icon
        icon_path = self.test_dir / "icon.png"
        Image.new("RGBA", (256, 256), color=(255, 100, 50, 255)).save(icon_path)

        builder = IPABuilder()
        res = builder.build_from_directory(
            source_dir=str(self.test_dir),
            app_name="GalacticArcade",
            bundle_id="com.web2ipa.galacticarcade",
            version_name="1.0.0",
            icon_path=str(icon_path)
        )

        self.assertTrue(res["success"])
        self.assertTrue(Path(res["ipa_path"]).exists())
        self.assertTrue(Path(res["mobileconfig_path"]).exists())
        self.assertTrue(Path(res["xcodeproj_zip_path"]).exists())
        self.assertTrue(Path(res["manifest_path"]).exists())

        # Verify target_web_url is properly configured with LAN IP and app route
        self.assertIn("target_web_url", res)
        self.assertNotIn("127.0.0.1", res["target_web_url"])
        self.assertNotIn("/download/", res["target_web_url"])
        self.assertIn("/app/GalacticArcade/index.html", res["target_web_url"])

        # Verify staged assets are preserved in OUTPUT_DIR / apps / GalacticArcade
        staged_app_index = OUTPUT_DIR / "apps" / "GalacticArcade" / "index.html"
        self.assertTrue(staged_app_index.exists())

        # Cleanup generated test files in OUTPUT_DIR
        for k in ["ipa_path", "mobileconfig_path", "xcodeproj_zip_path", "manifest_path"]:
            p = Path(res[k])
            if p.exists():
                p.unlink()

        shutil.rmtree(OUTPUT_DIR / "apps" / "GalacticArcade", ignore_errors=True)

if __name__ == "__main__":
    unittest.main()
