import unittest
import tempfile
import shutil
import zipfile
import json
from pathlib import Path
from fastapi.testclient import TestClient

from web2ipa.gui.server import app, OUTPUT_DIR

class TestGUIServer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.temp_dir = Path(tempfile.mkdtemp(prefix="test_gui_"))

        # Create a sample built app in OUTPUT_DIR for download tests
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.test_ipa = OUTPUT_DIR / "Sample_App-v1.0.0.ipa"
        cls.test_ipa.write_bytes(b"PK\x03\x04test_ipa_content")

        cls.test_mobileconfig = OUTPUT_DIR / "Sample_App.mobileconfig"
        cls.test_mobileconfig.write_text("<plist><dict></dict></plist>", encoding="utf-8")

        cls.test_zip = OUTPUT_DIR / "Sample_App-v1.0.0-XcodeProject.zip"
        cls.test_zip.write_bytes(b"PK\x03\x04test_xcode_zip")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
        for f in [cls.test_ipa, cls.test_mobileconfig, cls.test_zip]:
            if f.exists():
                f.unlink()

    def test_get_index(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Web2IPA", response.text)
        self.assertIn("AI Studio", response.text)

    def test_get_growth(self):
        response = self.client.get("/api/growth")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("level", data)
        self.assertIn("xp", data)
        self.assertIn("rank", data)

    def test_get_models(self):
        response = self.client.get("/api/models")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("models", data)

    def test_set_model(self):
        response = self.client.post("/api/set-model", data={"model_name": "gemini-2.5-flash"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_security_audit_code(self):
        snippet = "var key = 'AKIA1234567890123456'; eval('alert(1)');"
        response = self.client.post("/api/security-audit", data={"code_snippet": snippet})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("report", data)
        self.assertGreater(data["report"]["total_issues"], 0)

    def test_surprise_me(self):
        response = self.client.post("/api/surprise-me", data={"app_name": "Game Studio"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("innovations", data)
        self.assertGreater(len(data["innovations"]), 0)

    def test_get_innovations(self):
        response = self.client.get("/api/innovations")
        self.assertEqual(response.status_code, 200)
        self.assertIn("innovations", response.json())

    def test_inspect_folder(self):
        sample_folder = self.temp_dir / "web_app"
        sample_folder.mkdir()
        (sample_folder / "index.html").write_text("<title>Super Fast App</title>", encoding="utf-8")

        response = self.client.post("/api/inspect", data={"mode": "folder", "path": str(sample_folder)})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["app_name"], "Super Fast App")

    def test_qr_code(self):
        response = self.client.get("/api/qr-code?url=http://example.com/download")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["qr_code_base64"].startswith("data:image/png;base64,"))

    def test_download_landing_page(self):
        response = self.client.get(f"/download/{self.test_ipa.name}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("Sample App", response.text)
        self.assertIn("1-Tap Install", response.text)

    def test_download_raw(self):
        response = self.client.get(f"/download-raw/{self.test_ipa.name}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"PK\x03\x04test_ipa_content")

    def test_install_profile_mime_type(self):
        # CRITICAL TEST: verifies application/x-apple-aspen-config MIME type and attachment disposition for iOS Safari!
        response = self.client.get(f"/install-profile/{self.test_mobileconfig.name}")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("application/x-apple-aspen-config"))
        self.assertIn("attachment", response.headers.get("content-disposition", ""))

    def test_serve_app_assets(self):
        # Verify /app/{slug} serves HTML and assets with correct MIME types
        test_app_dir = OUTPUT_DIR / "apps" / "TestWebApp"
        test_app_dir.mkdir(parents=True, exist_ok=True)
        (test_app_dir / "index.html").write_text("<!DOCTYPE html><html><body><h1>Running on iPhone</h1></body></html>", encoding="utf-8")
        (test_app_dir / "app.js").write_text("console.log('test');", encoding="utf-8")

        # Test index.html
        resp = self.client.get("/app/TestWebApp/index.html")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/html", resp.headers["content-type"])
        self.assertIn("Running on iPhone", resp.text)

        # Test root /app/TestWebApp/
        resp_root = self.client.get("/app/TestWebApp/")
        self.assertEqual(resp_root.status_code, 200)
        self.assertIn("text/html", resp_root.headers["content-type"])

        # Test JS asset
        resp_js = self.client.get("/app/TestWebApp/app.js")
        self.assertEqual(resp_js.status_code, 200)
        self.assertIn("javascript", resp_js.headers["content-type"])

        # Cleanup
        shutil.rmtree(test_app_dir, ignore_errors=True)

    def test_build_zip_upload(self):
        # Create a test zip file
        zip_path = self.temp_dir / "mini_app.zip"
        with zipfile.ZipFile(zip_path, "w") as z:
            z.writestr("index.html", "<!DOCTYPE html><html><head><title>MiniApp</title></head><body><h1>Hello</h1></body></html>")

        with open(zip_path, "rb") as zf:
            response = self.client.post(
                "/api/build",
                data={
                    "mode": "zip",
                    "app_name": "MiniApp",
                    "bundle_id": "com.web2ipa.miniapp",
                    "version_name": "1.0.0",
                    "screen_orientation": "sensor",
                    "is_fullscreen": "true",
                    "theme_color": "#000000"
                },
                files={"file": ("mini_app.zip", zf, "application/zip")}
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"), msg=data.get("error"))
        self.assertIn("MiniApp", data["ipa_name"])
        self.assertIn("download_url", data)
        self.assertIn("qr_code_base64", data)
        self.assertIn("ipa_download_url", data)
        self.assertIn("profile_download_url", data)
        self.assertIn("zip_download_url", data)

        # Cleanup generated deliverables
        for key in ["ipa_path", "mobileconfig_path", "xcodeproj_zip_path", "manifest_path"]:
            p = Path(data[key])
            if p.exists():
                p.unlink()

    def test_upload_custom_icon(self):
        icon_path = self.temp_dir / "my_custom_logo.png"
        icon_path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x20\x00\x00\x00\x20\x08\x06\x00\x00\x00\x73z\x7a\xf4")

        with open(icon_path, "rb") as f:
            resp = self.client.post("/api/upload-icon", files={"icon_file": ("my_custom_logo.png", f, "image/png")}, data={"app_name": "Test App"})

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"), msg=data.get("error"))
        self.assertIn("icon_path", data)
        self.assertTrue(Path(data["icon_path"]).exists())
        self.assertIn("icon_base64", data)
        self.assertTrue(data["icon_base64"].startswith("data:image/png;base64,"))

    def test_inspect_zip_autodetects_logo(self):
        zip_path = self.temp_dir / "logo_project.zip"
        dummy_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x20\x00\x00\x00\x20\x08\x06\x00\x00\x00\x73z\x7a\xf4"
        with zipfile.ZipFile(zip_path, "w") as z:
            z.writestr("index.html", "<!DOCTYPE html><html><head><title>LogoApp</title></head><body><h1>Hello</h1></body></html>")
            z.writestr("assets/brand_logo.png", dummy_png)

        with open(zip_path, "rb") as zf:
            resp = self.client.post("/api/inspect", data={"mode": "zip"}, files={"file": ("logo_project.zip", zf, "application/zip")})

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"), msg=data.get("error"))
        self.assertIsNotNone(data.get("local_logo_path"))
        self.assertTrue(Path(data["local_logo_path"]).exists())
        self.assertIsNotNone(data.get("logo_base64"))
        self.assertTrue(data["logo_base64"].startswith("data:image/png;base64,"))

    def test_index_contains_downloads_and_sharing(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text

        # Verify Download actions are present in Deliverables Hub modal
        self.assertIn('id="modal-dl-ipa"', html)
        self.assertIn('id="modal-dl-profile"', html)
        self.assertIn('id="modal-dl-zip"', html)

        # Verify Simulator contains direct download and share controls
        self.assertIn('id="sim-top-dl-ipa"', html)
        self.assertIn('id="sim-top-dl-profile"', html)
        self.assertIn('id="sim-footer-dl-ipa"', html)
        self.assertIn('id="sim-footer-dl-profile"', html)

        # Verify Share App capabilities
        self.assertIn('shareApp()', html)
        self.assertIn('shareViaWhatsApp()', html)
        self.assertIn('id="modal-share-input"', html)

    def test_landing_page_contains_downloads_and_sharing(self):
        response = self.client.get("/download/Sample_App-v1.0.0.ipa")
        self.assertEqual(response.status_code, 200)
        html = response.text

        # Verify download links
        self.assertIn('/install-profile/', html)
        self.assertIn('/download-raw/', html)

        # Verify share functions
        self.assertIn('shareLandingPage()', html)
        self.assertIn('shareWhatsApp()', html)

if __name__ == "__main__":
    unittest.main()

