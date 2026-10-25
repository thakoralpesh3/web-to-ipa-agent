"""
Web2IPA AI Studio • Project Chhaya Architecture Mobile Access Manager
Enables seamless access from mobile devices (iPhones & iPads) via:
1. Public Worldwide 4G/5G HTTPS Link (Cloudflare Quick Tunnel)
2. Local Wi-Fi / Hotspot LAN Direct Link (e.g. http://10.27.31.178:8992)
3. Instant 1-Scan Mobile QR Code
"""

import os
import sys
import time
import json
import re
import socket
import base64
import io
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Dict, Any, Optional

STATE_DIR = Path.home() / ".web2ipa"
STATE_FILE = STATE_DIR / "mobile_access.json"
TUNNEL_LOG = STATE_DIR / "mobile_tunnel.log"

def find_cloudflared_bin() -> Optional[Path]:
    """Finds available cloudflared binary across standard locations."""
    candidates = [
        Path.home() / ".local" / "bin" / "cloudflared",
        Path.home() / "bin" / "cloudflared",
        Path("/home/alpesh/.local/bin/cloudflared"),
        Path("/home/alpesh/bin/cloudflared"),
        Path("/home/alpesh/chamunda_re_enterprise/bin/cloudflared"),
        Path("/usr/local/bin/cloudflared"),
        Path("/usr/bin/cloudflared")
    ]
    for c in candidates:
        if c.exists() and os.access(c, os.X_OK):
            return c
    # Check PATH
    which_bin = shutil.which("cloudflared")
    if which_bin:
        p = Path(which_bin)
        if p.exists() and os.access(p, os.X_OK):
            return p
    return None

def get_local_lan_ip() -> str:
    """Discovers primary local LAN Wi-Fi IP accessible by mobile devices."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass

    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            candidate = info[4][0]
            if ":" not in candidate and not candidate.startswith("127."):
                return candidate
    except Exception:
        pass

    return "127.0.0.1"

def generate_qr_base64(url: str) -> str:
    """Generates base64 PNG data URL for any given target URL."""
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0a84ff", back_color="#000000")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64}"
    except Exception as e:
        print(f"[MobileAccess] Error generating QR: {e}")
        return ""

class MobileAccessManager:
    """
    Manages 24/7 Mobile Remote Access for Web2IPA Studio, mirroring Project Chhaya.
    """
    _instance: Optional["MobileAccessManager"] = None
    _lock = threading.Lock()

    def __init__(self, port: int = 8992):
        self.port = port
        self.tunnel_proc: Optional[subprocess.Popen] = None
        self.public_url: Optional[str] = None
        self.cloudflared_bin = find_cloudflared_bin()
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self._load_cached_state()

    @classmethod
    def get_instance(cls, port: int = 8992) -> "MobileAccessManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(port=port)
            return cls._instance

    def _load_cached_state(self):
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.public_url = data.get("public_url")
            except Exception:
                pass

    def _save_state(self):
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "port": self.port,
                    "public_url": self.public_url,
                    "local_ip": get_local_lan_ip(),
                    "tunnel_active": self.is_tunnel_running(),
                    "updated_at": time.time()
                }, f, indent=2)
        except Exception:
            pass

    def is_tunnel_running(self) -> bool:
        return bool(self.tunnel_proc and self.tunnel_proc.poll() is None)

    def start_tunnel(self, wait_timeout: float = 12.0) -> Optional[str]:
        """
        Starts Cloudflare Quick Tunnel subprocess in background.
        Extracts and returns the public https://*.trycloudflare.com URL.
        """
        if self.is_tunnel_running() and self.public_url:
            return self.public_url

        if not self.cloudflared_bin:
            self.cloudflared_bin = find_cloudflared_bin()
            if not self.cloudflared_bin:
                print("[MobileAccess] cloudflared binary not found; skipping public tunnel.")
                return None

        # Stop existing dead process if any
        if self.tunnel_proc:
            try:
                self.tunnel_proc.terminate()
            except Exception:
                pass

        try:
            log_f = open(TUNNEL_LOG, "w", encoding="utf-8")
            self.tunnel_proc = subprocess.Popen(
                [str(self.cloudflared_bin), "tunnel", "--url", f"http://127.0.0.1:{self.port}"],
                stdout=log_f,
                stderr=log_f,
                start_new_session=True
            )

            # Wait for public URL to appear in log
            start_time = time.time()
            while time.time() - start_time < wait_timeout:
                time.sleep(0.5)
                if TUNNEL_LOG.exists():
                    try:
                        with open(TUNNEL_LOG, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            m = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", content)
                            if m:
                                self.public_url = m.group(0)
                                self._save_state()
                                print(f"[MobileAccess] 🌐 Public Worldwide Mobile URL: {self.public_url}")
                                return self.public_url
                    except Exception:
                        pass
                if self.tunnel_proc.poll() is not None:
                    break

        except Exception as e:
            print(f"[MobileAccess] Error starting tunnel: {e}")

        return None

    def stop_tunnel(self):
        """Stops the active Cloudflare Tunnel."""
        if self.tunnel_proc:
            try:
                self.tunnel_proc.terminate()
                self.tunnel_proc.wait(timeout=2)
            except Exception:
                try:
                    self.tunnel_proc.kill()
                except Exception:
                    pass
            self.tunnel_proc = None
        self.public_url = None
        self._save_state()

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns comprehensive mobile access telemetry and scannable QR code."""
        local_ip = get_local_lan_ip()
        local_url = f"http://{local_ip}:{self.port}"
        active_url = self.public_url if (self.is_tunnel_running() and self.public_url) else local_url
        qr_b64 = generate_qr_base64(active_url)

        return {
            "success": True,
            "port": self.port,
            "local_ip": local_ip,
            "local_url": local_url,
            "public_url": self.public_url,
            "active_mobile_url": active_url,
            "tunnel_active": self.is_tunnel_running(),
            "cloudflared_available": bool(self.cloudflared_bin),
            "qr_code_base64": qr_b64
        }

    def print_terminal_banner(self):
        """Displays rich terminal card with ASCII QR Code and direct mobile URLs."""
        try:
            from rich.console import Console
            from rich.panel import Panel
            from rich.table import Table
            console = Console()
        except ImportError:
            console = None

        telemetry = self.get_telemetry()
        active_url = telemetry["active_mobile_url"]

        # Generate ASCII QR Code
        ascii_qr = ""
        try:
            import qrcode
            qr = qrcode.QRCode(border=1)
            qr.add_data(active_url)
            qr.make(fit=True)
            f = io.StringIO()
            qr.print_ascii(out=f, invert=True)
            ascii_qr = f.getvalue()
        except Exception:
            pass

        banner_content = f"""[bold blue]📱 PROJECT CHHAYA MOBILE ACCESS READY (iOS Studio)[/bold blue]
[bold white]Control Web2IPA Studio directly from your iPhone or iPad:[/bold white]

[bold yellow]🌐 Worldwide 4G/5G Public Link:[/bold yellow]
  [underline cyan]{telemetry['public_url'] or 'Starting tunnel...'}[/underline cyan]

[bold green]📶 Local Wi-Fi / Hotspot LAN Link:[/bold green]
  [underline green]{telemetry['local_url']}[/underline green]

[bold magenta]📷 Scan QR Code with iPhone Camera to Open Web Studio:[/bold magenta]
{ascii_qr}
"""
        if console:
            console.print(Panel(banner_content.strip(), border_style="blue", title="[bold blue]📱 Mobile Remote Access (Web2IPA)[/bold blue]", expand=False))
        else:
            print("\n" + "="*60)
            print("📱 PROJECT CHHAYA MOBILE ACCESS READY (Web2IPA)")
            print(f"🌐 Worldwide Public Link: {telemetry['public_url'] or 'Starting tunnel...'}")
            print(f"📶 Local Wi-Fi LAN Link: {telemetry['local_url']}")
            print("="*60 + "\n")
