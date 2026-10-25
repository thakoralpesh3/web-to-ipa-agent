import unittest
import tempfile
import shutil
import json
from pathlib import Path
from PIL import Image

from web2ipa.icon_generator import iOSIconGenerator

class TestIOSIconGenerator(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_icons_"))

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_generate_apple_icon_catalog(self):
        # Create a dummy 512x512 PNG
        src_png = self.test_dir / "logo.png"
        img = Image.new("RGBA", (512, 512), color=(10, 132, 255, 255))
        img.save(src_png)

        out_catalog = self.test_dir / "AppIcon.appiconset"
        res = iOSIconGenerator.generate_apple_icon_catalog(
            output_dir=out_catalog,
            source_icon_path=str(src_png),
            app_name="Cyber Arcade"
        )

        self.assertTrue(res["success"])
        self.assertTrue((out_catalog / "Contents.json").exists())

        # Validate Contents.json format
        with open(out_catalog / "Contents.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("images", data)
        self.assertGreaterEqual(len(data["images"]), 18)

        # Validate marketing 1024x1024 App Store icon
        app_store_icon = out_catalog / "AppIcon-1024.png"
        self.assertTrue(app_store_icon.exists())
        with Image.open(app_store_icon) as im:
            self.assertEqual(im.size, (1024, 1024))

        # Validate iPhone 60pt @3x (180x180)
        phone_icon = out_catalog / "AppIcon-60@3x.png"
        self.assertTrue(phone_icon.exists())
        with Image.open(phone_icon) as im:
            self.assertEqual(im.size, (180, 180))

if __name__ == "__main__":
    unittest.main()
