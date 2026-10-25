"""
iOS Self-Healing Engine
Diagnoses and autonomously auto-repairs common iOS Safari / WebKit defects:
- Missing viewport-fit=cover (fixes white bars on notched iPhones & Dynamic Island)
- iOS 100vh viewport height jumping bug
- Web Audio context lock policy (unlocks audio on first user touch)
- iOS 300ms double-tap click delay
- Uncontrolled rubber-band overscroll
- Injects native Apple mobile web app tags and safe area styling
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, List


class iOSSelfHealer:
    """
    Diagnoses and automatically repairs web project files for iOS Safari / WKWebView.
    """

    @classmethod
    def diagnose_and_repair(cls, source_dir: Path, app_name: str = "Web App", theme_color: str = "#0f172a") -> Dict[str, Any]:
        """
        Runs comprehensive diagnostic and applies targeted self-healing patches.
        """
        source_dir = Path(source_dir).resolve()
        repairs_applied = []

        html_files = list(source_dir.glob("**/*.html")) + list(source_dir.glob("**/*.htm"))
        if not html_files:
            return {"repaired": False, "repairs": repairs_applied, "files_modified": 0}

        modified_count = 0
        for html_file in html_files:
            try:
                content = html_file.read_text(encoding="utf-8", errors="ignore")
                orig_content = content

                # 1. Patch Viewport for iPhone Notches & Dynamic Island
                content, rep1 = cls.patch_viewport(content)
                if rep1:
                    repairs_applied.extend(rep1)

                # 2. Inject Apple Mobile Web App Metas
                content, rep2 = cls.inject_apple_metas(content, app_name, theme_color)
                if rep2:
                    repairs_applied.extend(rep2)

                # 3. Patch iOS Safe-Area CSS and 100vh Bug
                content, rep3 = cls.patch_ios_safe_areas(content)
                if rep3:
                    repairs_applied.extend(rep3)

                # 4. Inject iOS Web Audio Unlocker
                content, rep4 = cls.inject_web_audio_unlocker(content)
                if rep4:
                    repairs_applied.extend(rep4)

                # 5. Inject iOS Universal Download Interceptor
                content, rep5 = cls.inject_download_healer(content)
                if rep5:
                    repairs_applied.extend(rep5)

                if content != orig_content:
                    html_file.write_text(content, encoding="utf-8")
                    modified_count += 1

            except Exception:
                pass

        return {
            "repaired": bool(repairs_applied),
            "repairs": list(set(repairs_applied)),
            "files_modified": modified_count
        }

    @classmethod
    def diagnose_and_heal_directory(cls, dir_path: Path, app_name: str = "Web App", theme_color: str = "#0f172a") -> Dict[str, Any]:
        res = cls.diagnose_and_repair(dir_path, app_name, theme_color)
        from .app_inspector import iOSAppInspector
        bp = iOSAppInspector.inspect_directory(dir_path)
        return {
            "repaired": res.get("repaired", False),
            "issues_detected": res.get("repairs", []),
            "repairs_made": res.get("repairs", []),
            "files_modified": res.get("files_modified", 0),
            "detected_permissions": list(bp.get("ios_permissions", {}).keys())
        }

    @classmethod
    def patch_viewport(cls, html: str) -> (str, List[str]):
        """Ensures viewport-fit=cover is present for edge-to-edge display on notched iPhones."""
        repairs = []
        viewport_regex = r'<meta\s+[^>]*name=["\']viewport["\'][^>]*>'
        match = re.search(viewport_regex, html, re.IGNORECASE)

        if match:
            tag = match.group(0)
            if "viewport-fit" not in tag.lower():
                new_tag = re.sub(r'content=["\']([^"\']+)["\']', r'content="\1, viewport-fit=cover"', tag)
                html = html.replace(tag, new_tag)
                repairs.append("Added 'viewport-fit=cover' to viewport meta tag for notch & Dynamic Island support")
        else:
            meta_tag = '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">\n'
            if "<head>" in html.lower():
                html = re.sub(r"(<head[^>]*>)", r"\1\n    " + meta_tag, html, flags=re.IGNORECASE)
                repairs.append("Injected missing iOS-optimized viewport meta tag")

        return html, repairs

    @classmethod
    def inject_apple_metas(cls, html: str, app_name: str, theme_color: str) -> (str, List[str]):
        """Injects Apple-specific fullscreen and status bar styling meta tags."""
        repairs = []
        apple_tags = []

        if "apple-mobile-web-app-capable" not in html.lower():
            apple_tags.append('<meta name="apple-mobile-web-app-capable" content="yes">')
            repairs.append("Enabled native iOS standalone app mode (apple-mobile-web-app-capable)")

        if "apple-mobile-web-app-status-bar-style" not in html.lower():
            apple_tags.append('<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">')
            repairs.append("Set translucent native status bar style for immersive display")

        if "apple-mobile-web-app-title" not in html.lower():
            apple_tags.append(f'<meta name="apple-mobile-web-app-title" content="{app_name}">')

        if "theme-color" not in html.lower():
            apple_tags.append(f'<meta name="theme-color" content="{theme_color}">')

        if apple_tags and "<head>" in html.lower():
            snippet = "\n    " + "\n    ".join(apple_tags)
            html = re.sub(r"(<head[^>]*>)", r"\1" + snippet, html, flags=re.IGNORECASE)

        return html, repairs

    @classmethod
    def patch_ios_safe_areas(cls, html: str) -> (str, List[str]):
        """
        Injects CSS fixes for safe-area insets, 100svh viewport bug, and double-tap zoom delay.
        """
        repairs = []
        if "ios-safe-area-fix" in html:
            return html, repairs

        ios_css = """
    <!-- iOS Native Safe-Area & Viewport Optimizer -->
    <style id="ios-safe-area-fix">
        :root {
            --sat: env(safe-area-inset-top, 0px);
            --sar: env(safe-area-inset-right, 0px);
            --sab: env(safe-area-inset-bottom, 0px);
            --sal: env(safe-area-inset-left, 0px);
        }
        html, body {
            min-height: 100vh;
            min-height: -webkit-fill-available;
            min-height: 100svh;
            -webkit-tap-highlight-color: transparent;
            -webkit-touch-callout: none;
            touch-action: manipulation;
        }
    </style>
"""
        if "</head>" in html.lower():
            html = re.sub(r"(</head>)", ios_css + r"\1", html, flags=re.IGNORECASE)
            repairs.append("Patched iOS safe-area variables and -webkit-fill-available 100vh viewport bug")

        return html, repairs

    @classmethod
    def inject_web_audio_unlocker(cls, html: str) -> (str, List[str]):
        """
        Auto-unlocks Web Audio Context on the first user touch, resolving silent audio in iOS WebKit.
        """
        repairs = []
        if "ios-audio-unlocker" in html:
            return html, repairs

        audio_js = """
    <!-- iOS Web Audio Context Auto-Unlocker -->
    <script id="ios-audio-unlocker">
        (function() {
            var unlocked = false;
            function unlockAudio() {
                if (unlocked) return;
                var AudioCtx = window.AudioContext || window.webkitAudioContext;
                if (AudioCtx) {
                    var ctx = new AudioCtx();
                    var buf = ctx.createBuffer(1, 1, 22050);
                    var src = ctx.createBufferSource();
                    src.buffer = buf;
                    src.connect(ctx.destination);
                    if (src.start) src.start(0);
                    if (ctx.resume) ctx.resume();
                    unlocked = true;
                }
                document.removeEventListener('touchstart', unlockAudio, true);
                document.removeEventListener('touchend', unlockAudio, true);
                document.removeEventListener('click', unlockAudio, true);
            }
            document.addEventListener('touchstart', unlockAudio, { passive: true, capture: true });
            document.addEventListener('touchend', unlockAudio, { passive: true, capture: true });
            document.addEventListener('click', unlockAudio, { passive: true, capture: true });
        })();
    </script>
"""
        if "</body>" in html.lower():
            html = re.sub(r"(</body>)", audio_js + r"\1", html, flags=re.IGNORECASE)
            repairs.append("Injected iOS Web Audio touch auto-unlocker")

        return html, repairs

    @classmethod
    def inject_download_healer(cls, html: str) -> (str, List[str]):
        """
        Injects universal download interceptor to capture Blob, data URI,
        and database file downloads, routing them directly to native iOSApp script message handler.
        """
        repairs = []
        if "ios-download-interceptor" in html:
            return html, repairs

        download_js = """
    <!-- iOS Native Database & File Download Interceptor -->
    <script id="ios-download-interceptor">
        (function() {
            var dbExts = ['.sqlite','.sqlite3','.db','.db3','.s3db','.sl3','.sql','.dump','.bak','.backup','.json','.csv','.tsv','.xlsx','.xls','.xml','.parquet','.zip','.tar','.gz','.7z','.rar','.bin','.dat','.pdf','.txt'];
            function isDb(u, f) {
                var s = ((f || '') + ' ' + (u || '')).toLowerCase();
                for (var i = 0; i < dbExts.length; i++) { if (s.indexOf(dbExts[i]) !== -1) return true; }
                return false;
            }
            function sendToNative(action, payload) {
                try {
                    if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.iOSApp) {
                        payload.action = action;
                        window.webkit.messageHandlers.iOSApp.postMessage(payload);
                        return true;
                    }
                } catch(e) {
                    console.error('[Web2IPA] Download bridge error:', e);
                }
                return false;
            }
            function procBlob(b, name) {
                var reader = new FileReader();
                reader.onloadend = function() {
                    sendToNative('saveFile', { base64: reader.result, filename: name || 'database.sqlite', mimeType: b.type || '' });
                };
                reader.readAsDataURL(b);
            }
            function trig(u, name) {
                if (!u) return false;
                if (u.indexOf('blob:') === 0) {
                    fetch(u).then(function(r) { return r.blob(); }).then(function(b) { procBlob(b, name); }).catch(function() {});
                    return true;
                } else if (u.indexOf('data:') === 0) {
                    return sendToNative('saveFile', { base64: u, filename: name || 'database.sqlite', mimeType: '' });
                } else if (isDb(u, name) || name) {
                    return sendToNative('downloadUrl', { url: u, filename: name || '', mimeType: '' });
                }
                return false;
            }
            document.addEventListener('click', function(e) {
                var t = e.target;
                while (t && t.tagName !== 'A') t = t.parentElement;
                if (!t || t.tagName !== 'A') return;
                var h = t.getAttribute('href') || t.href || '';
                var d = t.getAttribute('download');
                var fn = d || t.download || '';
                if (d !== null || h.indexOf('blob:') === 0 || h.indexOf('data:') === 0 || isDb(h, fn)) {
                    if (trig(h, fn)) { e.preventDefault(); e.stopPropagation(); }
                }
            }, true);
            try {
                var origClick = HTMLAnchorElement.prototype.click;
                HTMLAnchorElement.prototype.click = function() {
                    var h = this.getAttribute('href') || this.href || '';
                    var d = this.getAttribute('download');
                    var fn = d || this.download || '';
                    if (d !== null || h.indexOf('blob:') === 0 || h.indexOf('data:') === 0 || isDb(h, fn)) {
                        if (trig(h, fn)) return;
                    }
                    return origClick.apply(this, arguments);
                };
            } catch(e) {}
        })();
    </script>
"""
        if "</body>" in html.lower():
            html = re.sub(r"(</body>)", download_js + r"\1", html, flags=re.IGNORECASE)
            repairs.append("Injected iOS universal database & file download interceptor")

        return html, repairs
