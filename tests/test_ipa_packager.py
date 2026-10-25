import unittest
import tempfile
import shutil
import zipfile
import struct
from pathlib import Path
from PIL import Image

from web2ipa.ipa_packager import IPAPackager

class TestIPAPackager(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_ipa_"))

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_generate_mobileconfig(self):
        # Create dummy icon
        icon_path = self.test_dir / "icon.png"
        Image.new("RGBA", (180, 180), color=(10, 132, 255, 255)).save(icon_path)

        out_mobileconfig = self.test_dir / "TestApp.mobileconfig"
        IPAPackager.generate_mobileconfig(
            output_path=out_mobileconfig,
            app_name="Quantum Game",
            target_url="https://quantum.example.com",
            icon_png_path=str(icon_path),
            bundle_id="com.web2ipa.quantum"
        )

        self.assertTrue(out_mobileconfig.exists())
        content = out_mobileconfig.read_text(encoding="utf-8")
        self.assertIn("com.apple.webclip.managed", content)
        self.assertIn("Quantum Game", content)
        self.assertIn("https://quantum.example.com", content)
        self.assertIn("<key>FullScreen</key>", content)
        self.assertIn("<true/>", content)
        self.assertIn("<key>Icon</key>", content)

    def test_macho_arm64_stub_header(self):
        stub = IPAPackager.create_macho_arm64_stub()
        self.assertGreaterEqual(len(stub), 16384)

        # Check 64-bit Mach-O magic
        magic, cputype, cpusubtype, filetype = struct.unpack_from("<IIII", stub, 0)
        self.assertEqual(magic, 0xFEEDFACF)  # MH_MAGIC_64
        self.assertEqual(cputype, 0x0100000C)  # CPU_TYPE_ARM64
        self.assertEqual(filetype, 2)  # MH_EXECUTE

    def test_package_ipa(self):
        web_dir = self.test_dir / "www"
        web_dir.mkdir()
        (web_dir / "index.html").write_text("<h1>Hello iOS</h1>", encoding="utf-8")

        out_ipa = self.test_dir / "Quantum.ipa"
        IPAPackager.package_ipa(
            output_ipa_path=out_ipa,
            app_name="Quantum",
            bundle_id="com.web2ipa.quantum",
            version_name="1.0.0",
            web_assets_dir=web_dir,
            remote_url="https://quantum.example.com"
        )

        self.assertTrue(out_ipa.exists())

        # Verify ZIP bundle structure
        with zipfile.ZipFile(out_ipa, 'r') as z:
            names = z.namelist()
            self.assertIn("Payload/Quantum.app/Info.plist", names)
            self.assertIn("Payload/Quantum.app/PkgInfo", names)
            self.assertIn("Payload/Quantum.app/Quantum", names)
            self.assertIn("Payload/Quantum.app/www/index.html", names)

            # Check PkgInfo signature
            pkg_info = z.read("Payload/Quantum.app/PkgInfo")
            self.assertEqual(pkg_info, b"APPL????")

if __name__ == "__main__":
    unittest.main()
