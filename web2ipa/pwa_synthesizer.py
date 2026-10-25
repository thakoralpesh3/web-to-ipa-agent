import json
import os
import re
from pathlib import Path
from typing import Dict, Any, List

OFFLINE_HTML_FALLBACK = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>Offline Mode</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: #000000;
            color: #f5f5f7;
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
            text-align: center;
        }
        .card {
            background: rgba(28, 28, 30, 0.9);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 24px;
            padding: 32px 24px;
            max-width: 380px;
            width: 100%;
        }
        h2 { font-size: 1.4rem; margin-bottom: 8px; font-weight: 700; color: #fff; }
        p { color: #8e8e93; font-size: 0.95rem; margin-bottom: 24px; line-height: 1.5; }
        .btn {
            display: inline-block;
            background: #0a84ff;
            color: #fff;
            border: 0;
            padding: 14px 28px;
            border-radius: 14px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            width: 100%;
        }
    </style>
</head>
<body>
    <div class="card">
        <h2>Offline Mode</h2>
        <p>You are currently offline. Please check your network connection or try again.</p>
        <button class="btn" onclick="window.location.reload()">Retry Connection</button>
    </div>
</body>
</html>
"""

class PWASynthesizer:
    """
    Synthesizes iOS Web App meta tags, web manifests, and CacheStorage
    service workers into web assets.
    """

    @classmethod
    def generate_service_worker_code(cls, assets_to_cache: List[str]) -> str:
        assets_json = json.dumps(assets_to_cache, indent=4)
        return f"""/**
 * Web2IPA Autonomous Offline Service Worker for iOS WKWebView / Safari
 * Caches essential web bundle assets for instant offline execution.
 */
const CACHE_NAME = 'web2ipa-offline-v1';
const PRECACHE_ASSETS = {assets_json};

self.addEventListener('install', (event) => {{
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {{
            return Promise.allSettled(
                PRECACHE_ASSETS.map((url) => cache.add(url).catch((err) => {{
                    console.log('[SW] Optional asset skip:', url, err);
                }}))
            );
        }})
    );
    self.skipWaiting();
}});

self.addEventListener('activate', (event) => {{
    event.waitUntil(
        caches.keys().then((keyList) => {{
            return Promise.all(keyList.map((key) => {{
                if (key !== CACHE_NAME) {{
                    return caches.delete(key);
                }}
            }}));
        }})
    );
    self.clients.claim();
}});

self.addEventListener('fetch', (event) => {{
    if (event.request.method !== 'GET') return;

    event.respondWith(
        caches.match(event.request).then((cachedResponse) => {{
            if (cachedResponse) {{
                return cachedResponse;
            }}
            return fetch(event.request).then((networkResponse) => {{
                if (networkResponse && networkResponse.status === 200) {{
                    const responseToCache = networkResponse.clone();
                    caches.open(CACHE_NAME).then((cache) => {{
                        cache.put(event.request, responseToCache);
                    }});
                }}
                return networkResponse;
            }}).catch(() => {{
                if (event.request.mode === 'navigate') {{
                    return caches.match('offline.html').then((offResp) => {{
                        return offResp || new Response(`{OFFLINE_HTML_FALLBACK}`, {{
                            status: 200,
                            headers: new Headers({{ 'Content-Type': 'text/html; charset=utf-8' }})
                        }});
                    }});
                }}
                return new Response('Network error occurred', {{
                    status: 503,
                    statusText: 'Service Unavailable',
                    headers: new Headers({{ 'Content-Type': 'text/html; charset=utf-8' }})
                }});
            }});
        }})
    );
}});
"""

    @classmethod
    def synthesize_pwa_assets(
        cls,
        dir_path: Path,
        app_name: str = "iOS App",
        theme_color: str = "#000000",
        is_landscape: bool = False
    ) -> Dict[str, Any]:
        """
        Creates manifest.webmanifest, offline.html, sw.js, and injects iOS PWA meta tags
        into all HTML files in dir_path.
        """
        dir_path = Path(dir_path)

        # 1. Ensure offline.html exists
        offline_file = dir_path / "offline.html"
        if not offline_file.exists():
            offline_file.write_text(OFFLINE_HTML_FALLBACK, encoding="utf-8")

        # 2. Collect local web assets to precache
        precache_list = ["./", "index.html", "offline.html", "manifest.webmanifest"]
        valid_exts = {".html", ".htm", ".js", ".mjs", ".css", ".png", ".jpg", ".jpeg", ".svg", ".webp", ".json", ".wasm", ".ico"}
        for f in dir_path.rglob("*"):
            if f.is_file() and f.suffix.lower() in valid_exts:
                if f.name not in ["sw.js"] and f.stat().st_size < 10 * 1024 * 1024:
                    rel_p = str(f.relative_to(dir_path)).replace("\\", "/")
                    if rel_p not in precache_list:
                        precache_list.append(rel_p)

        # 3. Write Service Worker
        sw_file = dir_path / "sw.js"
        sw_code = cls.generate_service_worker_code(precache_list)
        sw_file.write_text(sw_code, encoding="utf-8")

        # 4. Write Web Manifest
        manifest_file = dir_path / "manifest.webmanifest"
        manifest_data = {
            "name": app_name,
            "short_name": app_name[:12],
            "start_url": "./index.html",
            "display": "standalone",
            "background_color": theme_color,
            "theme_color": theme_color,
            "orientation": "landscape" if is_landscape else "portrait",
            "icons": [
                {
                    "src": "apple-touch-icon.png",
                    "sizes": "180x180",
                    "type": "image/png"
                },
                {
                    "src": "icon-512.png",
                    "sizes": "512x512",
                    "type": "image/png"
                }
            ]
        }
        manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        # 5. Inject PWA and iOS Apple Mobile Web App tags into index.html
        html_files = list(dir_path.glob("**/*.html"))
        patched = 0
        pwa_tags = f"""
    <!-- Web2IPA Apple iOS & PWA Directives -->
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="{app_name}">
    <link rel="apple-touch-icon" href="apple-touch-icon.png">
    <link rel="manifest" href="manifest.webmanifest">
    <script>
      if ('serviceWorker' in navigator) {{
        window.addEventListener('load', () => {{
          navigator.serviceWorker.register('./sw.js').catch(() => {{}});
        }});
      }}
    </script>
"""
        for h in html_files:
            if h.name == "offline.html":
                continue
            try:
                content = h.read_text(encoding="utf-8", errors="ignore")
                if "apple-mobile-web-app-capable" not in content and "</head>" in content:
                    new_content = content.replace("</head>", f"{pwa_tags}\n</head>", 1)
                    h.write_text(new_content, encoding="utf-8")
                    patched += 1
            except Exception:
                pass

        return {
            "success": True,
            "sw_written": True,
            "manifest_written": True,
            "html_patched": patched,
            "cached_assets_count": len(precache_list)
        }
