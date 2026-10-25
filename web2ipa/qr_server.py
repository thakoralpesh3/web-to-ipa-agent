import io
import os
import re
import socket
import base64
import urllib.parse
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Union, Tuple
import mimetypes
import qrcode

OUTPUT_DIR = Path.home() / "Web2IPA_Output"

class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True

class QRServer:
    """
    Wi-Fi QR Sideload & OTA Server for iOS.
    Serves .mobileconfig (1-tap Safari WebClip installation), .ipa (AltStore/Sideloadly),
    and .xcodeproj.zip archives over local Wi-Fi with instant QR codes.
    """

    @staticmethod
    def get_local_ip() -> str:
        """Detects primary local LAN IP address accessible by iPhones/iPads on the Wi-Fi."""
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
                candidate_ip = info[4][0]
                if ":" not in candidate_ip and not candidate_ip.startswith("127."):
                    return candidate_ip
        except Exception:
            pass

        return "127.0.0.1"

    @classmethod
    def get_download_url(cls, filename: str, port: int = 8992, host: Optional[str] = None) -> str:
        if host and "localhost" not in host and "127.0.0.1" not in host:
            clean_host = host.rstrip("/")
            if not clean_host.startswith("http://") and not clean_host.startswith("https://"):
                clean_host = f"http://{clean_host}"
            return f"{clean_host}/download/{filename}"

        ip = cls.get_local_ip()
        return f"http://{ip}:{port}/download/{filename}"

    @classmethod
    def generate_terminal_qr(cls, text: str):
        """Prints high-contrast QR code directly to terminal."""
        qr = qrcode.QRCode(box_size=1, border=1)
        qr.add_data(text)
        qr.make()
        qr.print_ascii(invert=True)

    @classmethod
    def generate_qr_base64(cls, text: str) -> str:
        """Returns base64 encoded PNG for display in Web Studio."""
        qr = qrcode.QRCode(box_size=10, border=2)
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0a84ff", back_color="#000000")

        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"

    @classmethod
    def generate_landing_page_html(cls, filename: str, file_size_mb: float = 0, app_name: str = "") -> str:
        display_title = app_name or filename.replace(".ipa", "").replace(".mobileconfig", "").replace("_", " ")
        base_name = re.sub(r'(-v[0-9.]+(-XcodeProject)?)?\.(ipa|mobileconfig|zip)$', '', filename)

        # Resolve real files on disk to prevent 404s
        ipa_candidates = list(OUTPUT_DIR.glob(f"{base_name}*.ipa"))
        if ipa_candidates:
            ipa_candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            ipa_name = ipa_candidates[0].name
        else:
            ipa_name = f"{base_name}.ipa"

        zip_candidates = list(OUTPUT_DIR.glob(f"{base_name}*XcodeProject*.zip"))
        if zip_candidates:
            zip_candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            zip_name = zip_candidates[0].name
        else:
            zip_name = f"{base_name}-XcodeProject.zip"

        cfg_candidates = list(OUTPUT_DIR.glob(f"{base_name}*.mobileconfig"))
        if cfg_candidates:
            cfg_candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            mobileconfig_name = cfg_candidates[0].name
        else:
            mobileconfig_name = f"{base_name}.mobileconfig"

        # Check for live app launch target
        live_app_url = None
        mobileconfig_path = OUTPUT_DIR / mobileconfig_name
        if mobileconfig_path.exists():
            try:
                content = mobileconfig_path.read_text(encoding="utf-8")
                m = re.search(r'<key>URL</key>\s*<string>(.*?)</string>', content)
                if m:
                    target_candidate = m.group(1).strip()
                    if "/download/" not in target_candidate:
                        live_app_url = target_candidate
            except Exception:
                pass

        if not live_app_url:
            local_app_dir = OUTPUT_DIR / "apps" / base_name
            if local_app_dir.exists():
                live_app_url = f"/app/{base_name}/index.html"
            else:
                app_candidates = list((OUTPUT_DIR / "apps").glob(f"{base_name}*"))
                if app_candidates:
                    live_app_url = f"/app/{app_candidates[0].name}/index.html"
                else:
                    live_app_url = f"/app/{base_name}/index.html"

        live_btn_html = ""
        if live_app_url:
            live_btn_html = f"""
        <!-- Instant Live Web Application Launch -->
        <a href="{live_app_url}" class="btn btn-launch" target="_blank">
            🚀 Launch & Run Web App in Safari
        </a>
"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>{display_title} - iOS Install Studio</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: #000000;
            color: #f5f5f7;
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 24px;
            padding-top: env(safe-area-inset-top, 24px);
            padding-bottom: env(safe-area-inset-bottom, 24px);
        }}
        .card {{
            background: rgba(28, 28, 30, 0.85);
            backdrop-filter: blur(30px);
            -webkit-backdrop-filter: blur(30px);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 28px;
            box-shadow: 0 25px 60px rgba(0, 0, 0, 0.7);
            padding: 36px 28px;
            max-width: 440px;
            width: 100%;
            text-align: center;
        }}
        .apple-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(10, 132, 255, 0.15);
            color: #0a84ff;
            border: 1px solid rgba(10, 132, 255, 0.3);
            font-size: 0.75rem;
            font-weight: 700;
            padding: 6px 14px;
            border-radius: 9999px;
            margin-bottom: 20px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .icon-box {{
            width: 88px;
            height: 88px;
            background: linear-gradient(135deg, #0a84ff 0%, #5e5ce6 100%);
            border-radius: 20px;
            margin: 0 auto 20px auto;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 10px 25px rgba(10, 132, 255, 0.35);
        }}
        .icon-box svg {{
            width: 44px;
            height: 44px;
            fill: #ffffff;
        }}
        h1 {{
            font-size: 1.6rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-bottom: 6px;
        }}
        p.subtitle {{
            color: #8e8e93;
            font-size: 0.95rem;
            margin-bottom: 28px;
        }}
        .btn {{
            display: block;
            width: 100%;
            padding: 15px;
            border-radius: 14px;
            font-size: 1rem;
            font-weight: 600;
            text-decoration: none;
            margin-bottom: 12px;
            transition: all 0.15s ease;
            cursor: pointer;
            border: 0;
        }}
        .btn-launch {{
            background: linear-gradient(135deg, #30d158 0%, #28cd41 100%);
            color: #ffffff;
            box-shadow: 0 4px 20px rgba(48, 209, 88, 0.4);
        }}
        .btn-launch:active {{
            transform: scale(0.98);
            background: #24b338;
        }}
        .btn-primary {{
            background: #0a84ff;
            color: #ffffff;
            box-shadow: 0 4px 20px rgba(10, 132, 255, 0.4);
        }}
        .btn-primary:active {{
            transform: scale(0.98);
            background: #0071e3;
        }}
        .btn-secondary {{
            background: rgba(255, 255, 255, 0.08);
            color: #f5f5f7;
            border: 1px solid rgba(255, 255, 255, 0.12);
        }}
        .btn-secondary:active {{
            background: rgba(255, 255, 255, 0.15);
        }}
        .instructions {{
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 16px;
            padding: 16px;
            margin-top: 24px;
            text-align: left;
            font-size: 0.85rem;
            color: #a1a1a6;
            line-height: 1.6;
        }}
        .instructions ol {{
            padding-left: 20px;
            margin-top: 8px;
        }}
        .instructions li {{
            margin-bottom: 6px;
        }}
        .footer {{
            margin-top: 24px;
            font-size: 0.75rem;
            color: #636366;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="apple-badge">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M15.97 4.17c.61-.75 1.04-1.8 0.92-2.86-.9.04-2 .6-2.65 1.35-.56.64-1.06 1.7-0.93 2.73 1.01.08 2.05-.51 2.66-1.22z"/>
            </svg>
            iOS Ready
        </div>
        <div class="icon-box">
            <svg viewBox="0 0 24 24">
                <path d="M12 2a10 10 0 1010 10A10 10 0 0012 2zm1 14h-2v-2h2zm0-4h-2V7h2z"/>
            </svg>
        </div>
        <h1>{display_title}</h1>
        <p class="subtitle">Standalone Native iOS Application</p>

        <div id="browser-warning" style="display:none; background:rgba(255,159,10,0.15); border:1px solid rgba(255,159,10,0.4); border-radius:14px; padding:12px; margin-bottom:14px; color:#ff9f0a; font-size:0.82rem; text-align:left;">
            ⚠️ <strong>Please Open in Safari:</strong> Third-party browsers (Chrome, Firefox, In-App) cannot install iOS profiles directly. Tap the Share button &rarr; <strong>Open in Safari</strong>.
        </div>
{live_btn_html}
        <!-- 1-Tap Safari MobileConfig Installation -->
        <a href="/install-profile/{urllib.parse.quote(mobileconfig_name)}" class="btn btn-primary">
            ⚡ 1-Tap Install (WebClip Profile)
        </a>

        <!-- Sideload IPA -->
        <a href="/download-raw/{urllib.parse.quote(ipa_name)}" class="btn btn-secondary">
            📦 Download Sideload .IPA ({file_size_mb:.1f} MB)
        </a>

        <!-- Xcode Source Project -->
        <a href="/download-raw/{urllib.parse.quote(zip_name)}" class="btn btn-secondary">
            🛠️ Download Xcode Project (.ZIP)
        </a>

        <!-- Share App Section -->
        <div style="display: flex; gap: 8px; margin-bottom: 12px;">
            <button onclick="shareLandingPage()" class="btn btn-secondary" style="margin-bottom:0; display:flex; align-items:center; justify-content:center; gap:6px;">
                📤 Share App
            </button>
            <button onclick="shareWhatsApp()" class="btn btn-secondary" style="margin-bottom:0; display:flex; align-items:center; justify-content:center; gap:6px; color:#30d158; border-color:rgba(48,209,88,0.3);">
                💬 WhatsApp
            </button>
        </div>

        <div class="instructions">
            <strong>📲 How to Install & Run on iPhone / iPad:</strong>
            <ol>
                <li><strong>⚡ 1-Tap Direct Install (Recommended):</strong> Tap <strong>1-Tap Install</strong> in Safari. When Safari asks <em>"This website is trying to download a configuration profile. Do you want to allow this?"</em>, tap <strong>Allow</strong>.</li>
                <li><strong>Complete in Settings:</strong> Open iPhone <strong>Settings</strong> &rarr; tap <strong>Profile Downloaded</strong> (at the top) &rarr; tap <strong>Install</strong>. Your app icon will appear on your Home Screen!</li>
                <li><strong>🚀 Fast Alternative:</strong> Tap <strong>Launch Live Web App</strong> &rarr; in Safari tap Share &rarr; <strong>Add to Home Screen</strong>.</li>
                <li><strong>ℹ️ Why .IPA shows "Unable to preview":</strong> Raw <code>.ipa</code> files cannot be opened from the iOS Files app without AltStore/PC. For direct installation on your iPhone without a computer, use <strong>1-Tap Install</strong> above!</li>
            </ol>
        </div>

        <div class="footer">
            Generated with Web2IPA AI Studio &bull; iOS 15+ Compatible
        </div>
    </div>

    <script>
        (function() {{
            const ua = navigator.userAgent;
            const isIOS = /iPhone|iPad|iPod/.test(ua);
            const isNonSafari = /CriOS|FxiOS|EdgiOS|FBAN|FBAV|Instagram/.test(ua);
            if (isIOS && isNonSafari) {{
                const el = document.getElementById('browser-warning');
                if (el) el.style.display = 'block';
            }}
        }})();

        function shareLandingPage() {{
            const shareData = {{
                title: document.title,
                text: 'Install this iOS app on your iPhone / iPad:',
                url: window.location.href
            }};
            if (navigator.share) {{
                navigator.share(shareData).catch(() => {{}});
            }} else {{
                navigator.clipboard.writeText(window.location.href).then(() => {{
                    alert('✓ App download link copied to clipboard!');
                }}).catch(() => {{
                    prompt('Copy this link to share:', window.location.href);
                }});
            }}
        }}
        function shareWhatsApp() {{
            const msg = 'Install *' + document.title + '* on your iPhone / iPad:\\n' + window.location.href;
            window.open('https://api.whatsapp.com/send?text=' + encodeURIComponent(msg), '_blank');
        }}
    </script>
</body>
</html>
"""

class QRServerHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests for iOS downloads, profiles, and live web apps."""

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # 1. Configuration Profile (.mobileconfig) for 1-Tap Safari Installation
        if path.startswith("/install-profile/"):
            fname = urllib.parse.unquote(path.replace("/install-profile/", ""))
            file_path = OUTPUT_DIR / fname
            if file_path.exists():
                self.send_response(200)
                self.send_header("Content-Type", "application/x-apple-aspen-config")
                self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
                self.send_header("Content-Length", str(file_path.stat().st_size))
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
                return

        # 2. Live Web Application Hosting for iPhone WebClips & Safari
        if path.startswith("/app/"):
            app_subpath = path[len("/app/"):].lstrip("/")
            parts = app_subpath.split("/", 1)
            app_slug = parts[0]
            sub_file = parts[1] if len(parts) > 1 and parts[1] else "index.html"

            app_dir = (OUTPUT_DIR / "apps" / app_slug).resolve()
            target_file = (app_dir / sub_file).resolve()

            # Prevent directory traversal
            if str(target_file).startswith(str(app_dir)) and target_file.exists():
                if target_file.is_dir():
                    target_file = (target_file / "index.html").resolve()

                if target_file.exists() and target_file.is_file():
                    content_type, _ = mimetypes.guess_type(str(target_file))
                    if not content_type:
                        if target_file.suffix == ".html":
                            content_type = "text/html"
                        elif target_file.suffix in [".js", ".mjs"]:
                            content_type = "application/javascript"
                        elif target_file.suffix == ".css":
                            content_type = "text/css"
                        elif target_file.suffix in [".webmanifest", ".json"]:
                            content_type = "application/manifest+json"
                        elif target_file.suffix == ".wasm":
                            content_type = "application/wasm"
                        else:
                            content_type = "application/octet-stream"

                    if content_type in ["text/html", "text/css", "application/javascript"]:
                        content_type = f"{content_type}; charset=utf-8"

                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(target_file.stat().st_size))
                    self.send_header("Content-Disposition", f'inline; filename="{target_file.name}"')
                    self.end_headers()
                    with open(target_file, "rb") as f:
                        self.wfile.write(f.read())
                    return

        # 3. Raw Binary Downloads (.ipa, .zip)
        if path.startswith("/download-raw/"):
            fname = urllib.parse.unquote(path.replace("/download-raw/", ""))
            file_path = OUTPUT_DIR / fname
            if file_path.exists():
                self.send_response(200)
                media_type = "application/octet-stream"
                disposition = f'attachment; filename="{fname}"'
                if fname.endswith(".zip"):
                    media_type = "application/zip"
                elif fname.endswith(".mobileconfig"):
                    media_type = "application/x-apple-aspen-config"
                    disposition = f'attachment; filename="{fname}"'
                self.send_header("Content-Type", media_type)
                self.send_header("Content-Disposition", disposition)
                self.send_header("Content-Length", str(file_path.stat().st_size))
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
                return

        # 4. Cupertino Mobile Landing Page
        if path.startswith("/download/"):
            fname = urllib.parse.unquote(path.replace("/download/", ""))
            file_path = OUTPUT_DIR / fname
            if file_path.exists():
                size_mb = round(file_path.stat().st_size / (1024 * 1024), 2)
                html = QRServer.generate_landing_page_html(fname, size_mb)
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html.encode("utf-8"))
                return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"404 Not Found")

    def log_message(self, format, *args):
        pass

def run_server(port: int = 8992):
    server = ReusableHTTPServer(("0.0.0.0", port), QRServerHandler)
    server.serve_forever()

def start_server_in_background(port: int = 8992) -> threading.Thread:
    t = threading.Thread(target=run_server, args=(port,), daemon=True)
    t.start()
    return t
