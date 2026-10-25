import unittest
from starlette.testclient import TestClient

from web2ipa.mobile_access import (
    find_cloudflared_bin,
    get_local_lan_ip,
    generate_qr_base64,
    MobileAccessManager
)
from web2ipa.gui.server import app


class TestMobileAccess(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_find_cloudflared_bin(self):
        bin_path = find_cloudflared_bin()
        if bin_path:
            self.assertTrue(bin_path.exists())

    def test_get_local_lan_ip(self):
        ip = get_local_lan_ip()
        self.assertIsInstance(ip, str)
        parts = ip.split(".")
        self.assertEqual(len(parts), 4, f"Invalid IP format: {ip}")
        for part in parts:
            self.assertTrue(part.isdigit())
            self.assertTrue(0 <= int(part) <= 255)

    def test_generate_qr_base64(self):
        url = "http://10.27.31.178:8992"
        qr = generate_qr_base64(url)
        self.assertTrue(qr.startswith("data:image/png;base64,"))
        self.assertGreater(len(qr), 100)

    def test_mobile_access_manager_telemetry(self):
        mgr = MobileAccessManager.get_instance(port=8992)
        telemetry = mgr.get_telemetry()
        self.assertTrue(telemetry.get("success"))
        self.assertEqual(telemetry.get("port"), 8992)
        self.assertIn("local_ip", telemetry)
        self.assertIn("local_url", telemetry)
        self.assertIn("active_mobile_url", telemetry)
        self.assertIn("qr_code_base64", telemetry)
        self.assertTrue(telemetry["qr_code_base64"].startswith("data:image/png;base64,"))

    def test_terminal_banner_render(self):
        mgr = MobileAccessManager.get_instance(port=8992)
        # Should execute without throwing exception
        mgr.print_terminal_banner()

    def test_api_mobile_access_endpoint(self):
        resp = self.client.get("/api/mobile-access")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"))
        self.assertIn("local_url", data)
        self.assertIn("qr_code_base64", data)
        self.assertIn("cloudflared_available", data)

    def test_api_mobile_tunnel_controls(self):
        resp_stop = self.client.post("/api/mobile-access/stop-tunnel")
        self.assertEqual(resp_stop.status_code, 200)
        data_stop = resp_stop.json()
        self.assertTrue(data_stop.get("success"))
        self.assertFalse(data_stop.get("tunnel_active"))


if __name__ == "__main__":
    unittest.main()
