import unittest
from web2ipa.qr_server import QRServer

class TestIOSQRServer(unittest.TestCase):

    def test_local_ip(self):
        ip = QRServer.get_local_ip()
        self.assertIsInstance(ip, str)
        self.assertGreater(len(ip), 0)

    def test_download_url(self):
        url = QRServer.get_download_url("test_app.ipa", port=8992)
        self.assertIn(":8992/download/test_app.ipa", url)
        self.assertTrue(url.startswith("http://"))

    def test_qr_base64_generation(self):
        b64 = QRServer.generate_qr_base64("https://example.com/download")
        self.assertTrue(b64.startswith("data:image/png;base64,"))

    def test_landing_page_html(self):
        html = QRServer.generate_landing_page_html("CyberArcade.ipa", 12.5, "Cyber Arcade")
        self.assertIn("Cyber Arcade", html)
        self.assertIn(".mobileconfig", html)
        self.assertIn("1-Tap Install", html)
        self.assertIn("Standalone Native iOS Application", html)

if __name__ == "__main__":
    unittest.main()
