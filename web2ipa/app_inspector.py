"""
iOS Deep App Inspector
Analyzes web source directories, live URLs, or ZIP archives to autonomously extract
app metadata, reverse-domain bundle IDs, Apple touch icons, theme colors, orientations,
and required Apple iOS privacy usage descriptions (NSCameraUsageDescription, etc.).
"""

import os
import re
import json
import base64
import zipfile
import tempfile
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import requests

from .icon_generator import iOSIconGenerator


class iOSAppInspector:
    """
    Multi-source deep inspection engine for iOS.
    Automatically detects brand assets, configurations, and Apple privacy permissions.
    """

    SUPPORTED_ICON_EXTS = {".svg", ".png", ".jpg", ".jpeg", ".webp", ".ico"}

    @classmethod
    def inspect(cls, source: str) -> Dict[str, Any]:
        """
        Inspects directory path, live URL, or ZIP archive.
        """
        source_str = str(source).strip()
        if source_str.startswith(("http://", "https://")):
            return cls.inspect_url(source_str)

        src_path = Path(source_str).resolve()
        if not src_path.exists():
            raise FileNotFoundError(f"Source does not exist: {source_str}")

        if src_path.is_file() and src_path.suffix.lower() == ".zip":
            return cls.inspect_zip(src_path)

        if src_path.is_dir():
            return cls.inspect_directory(src_path)

        raise ValueError(f"Unsupported source type: {source_str}")

    @classmethod
    def inspect_directory(cls, dir_path: Path) -> Dict[str, Any]:
        """Deep inspection of a local web folder."""
        dir_path = Path(dir_path).resolve()
        blueprint = {
            "app_name": "Web App",
            "bundle_id": "com.web2ipa.app",
            "version_name": "1.0.0",
            "theme_color": "#0f172a",
            "orientation": "universal",  # universal (all), portrait, landscape
            "is_fullscreen": True,
            "device_family": "universal",  # universal, iphone, ipad
            "icon_path": None,
            "icon_base64": None,
            "ios_permissions": {},
            "detection_sources": {}
        }

        # 1. Inspect package.json if present
        pkg_json = dir_path / "package.json"
        if pkg_json.exists():
            try:
                with open(pkg_json, "r", encoding="utf-8") as f:
                    pkg_data = json.load(f)
                    if pkg_data.get("name"):
                        raw_name = pkg_data["name"]
                        blueprint["app_name"] = cls.clean_app_name(raw_name)
                        blueprint["bundle_id"] = cls.generate_bundle_id(raw_name)
                        blueprint["detection_sources"]["app_name"] = "package.json"
                    if pkg_data.get("version"):
                        blueprint["version_name"] = pkg_data["version"]
            except Exception:
                pass

        # 2. Inspect manifest.json / webmanifest
        manifest_files = list(dir_path.glob("**/manifest.json")) + list(dir_path.glob("**/*.webmanifest"))
        manifest_data = {}
        if manifest_files:
            try:
                with open(manifest_files[0], "r", encoding="utf-8") as f:
                    manifest_data = json.load(f)
                if manifest_data.get("name") or manifest_data.get("short_name"):
                    raw_name = manifest_data.get("name") or manifest_data.get("short_name")
                    blueprint["app_name"] = cls.clean_app_name(raw_name)
                    blueprint["bundle_id"] = cls.generate_bundle_id(raw_name)
                    blueprint["detection_sources"]["app_name"] = "Web Manifest"
                if manifest_data.get("theme_color"):
                    blueprint["theme_color"] = cls.normalize_hex_color(manifest_data["theme_color"])
                    blueprint["detection_sources"]["theme_color"] = "manifest.json"
                if manifest_data.get("orientation"):
                    ori = manifest_data["orientation"].lower()
                    if "portrait" in ori:
                        blueprint["orientation"] = "portrait"
                    elif "landscape" in ori:
                        blueprint["orientation"] = "landscape"
                if manifest_data.get("display") in ["standalone", "fullscreen"]:
                    blueprint["is_fullscreen"] = True
            except Exception:
                pass

        # 3. Inspect HTML files
        html_files = list(dir_path.glob("**/*.html"))
        if html_files:
            # Sort to prefer index.html
            index_candidates = [h for h in html_files if h.name.lower() == "index.html"]
            primary_html = index_candidates[0] if index_candidates else html_files[0]

            try:
                html_text = primary_html.read_text(encoding="utf-8", errors="ignore")
                cls._extract_from_html(html_text, primary_html.parent, blueprint)
            except Exception:
                pass

        # Fallback app name from directory name
        if blueprint["app_name"] == "Web App" and dir_path.name:
            clean_dir = cls.clean_app_name(dir_path.name)
            blueprint["app_name"] = clean_dir
            blueprint["bundle_id"] = cls.generate_bundle_id(clean_dir)
            blueprint["detection_sources"]["app_name"] = "Directory Name"

        # 4. Search for App Icons & Apple Touch Icons
        if not blueprint["icon_path"]:
            discovered_icon = cls._discover_local_icon(dir_path, manifest_data)
            if discovered_icon:
                blueprint["icon_path"] = str(discovered_icon)
                blueprint["detection_sources"]["icon"] = f"Local Asset ({discovered_icon.name})"

        # 5. Scan JS code for required Apple Privacy Permissions
        blueprint["ios_permissions"] = cls._detect_ios_permissions(dir_path)

        # 6. Normalize Icon to Cache
        if blueprint["icon_path"]:
            norm_path, b64 = iOSIconGenerator.cache_normalized_icon(blueprint["icon_path"], blueprint["app_name"])
            if norm_path:
                blueprint["icon_path"] = str(norm_path)
                blueprint["icon_base64"] = b64

        return blueprint

    @classmethod
    def inspect_url(cls, url: str) -> Dict[str, Any]:
        """Deep inspection of a remote live URL."""
        blueprint = {
            "app_name": "Web App",
            "bundle_id": "com.web2ipa.app",
            "version_name": "1.0.0",
            "theme_color": "#0f172a",
            "orientation": "universal",
            "is_fullscreen": True,
            "device_family": "universal",
            "icon_path": None,
            "icon_base64": None,
            "ios_permissions": {
                "NSCameraUsageDescription": "This app requires access to the camera for capturing photos and video.",
                "NSMicrophoneUsageDescription": "This app requires access to the microphone for audio and voice communication.",
                "NSLocationWhenInUseUsageDescription": "This app requires location access to provide location-based web features."
            },
            "detection_sources": {}
        }

        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc or "example.com"
        host_parts = [p for p in netloc.split(".") if p not in ["www", "m", "mobile", "app"]]
        slug = host_parts[0] if host_parts else "webapp"
        blueprint["app_name"] = cls.clean_app_name(slug)
        blueprint["bundle_id"] = cls.generate_bundle_id(netloc)
        blueprint["detection_sources"]["bundle_id"] = "Domain Reverse Slug"

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
            }
            resp = requests.get(url, headers=headers, timeout=12)
            if resp.status_code == 200:
                html_text = resp.text
                cls._extract_from_html_remote(html_text, url, blueprint)
        except Exception as e:
            blueprint["detection_sources"]["notice"] = f"URL request error: {e}"

        # Normalize and cache remote icon
        if blueprint["icon_path"]:
            norm_path, b64 = iOSIconGenerator.cache_normalized_icon(blueprint["icon_path"], blueprint["app_name"])
            if norm_path:
                blueprint["icon_path"] = str(norm_path)
                blueprint["icon_base64"] = b64

        return blueprint

    @classmethod
    def inspect_zip(cls, zip_path: Path) -> Dict[str, Any]:
        """Deep inspection of a ZIP archive."""
        temp_dir = Path(tempfile.mkdtemp(prefix="ios_zip_inspect_"))
        try:
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(temp_dir)
            htmls = list(temp_dir.glob("**/*.html"))
            target_dir = htmls[0].parent if htmls else temp_dir
            blueprint = cls.inspect_directory(target_dir)
            if blueprint.get("detection_sources", {}).get("app_name") == "Directory Name":
                blueprint["app_name"] = cls.clean_app_name(zip_path.stem)
                blueprint["bundle_id"] = cls.generate_bundle_id(zip_path.stem)

            if blueprint.get("icon_path") and Path(blueprint["icon_path"]).exists():
                norm_path, b64 = iOSIconGenerator.cache_normalized_icon(blueprint["icon_path"], blueprint.get("app_name", "App"))
                if norm_path:
                    blueprint["icon_path"] = str(norm_path)
                    blueprint["icon_base64"] = b64
            return blueprint
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    # --------------------------------------------------------------------------
    # INTERNAL EXTRACTION & DETECTION HELPERS
    # --------------------------------------------------------------------------

    @classmethod
    def _extract_from_html(cls, html_text: str, base_dir: Path, blueprint: Dict[str, Any]):
        """Extracts metadata, theme colors, and icons from local HTML."""
        # App Title
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", html_text, re.IGNORECASE)
        if title_match and title_match.group(1).strip():
            raw_title = title_match.group(1).strip().split("|")[0].split("-")[0].strip()
            if len(raw_title) >= 2:
                blueprint["app_name"] = cls.clean_app_name(raw_title)
                blueprint["bundle_id"] = cls.generate_bundle_id(raw_title)
                blueprint["detection_sources"]["app_name"] = "HTML <title>"

        # Meta application-name / apple-mobile-web-app-title
        app_meta = re.search(r'<meta\s+name=["\'](apple-mobile-web-app-title|application-name)["\']\s+content=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
        if app_meta:
            blueprint["app_name"] = cls.clean_app_name(app_meta.group(2))
            blueprint["detection_sources"]["app_name"] = f"Meta {app_meta.group(1)}"

        # Theme color
        theme_meta = re.search(r'<meta\s+name=["\']theme-color["\']\s+content=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
        if theme_meta:
            blueprint["theme_color"] = cls.normalize_hex_color(theme_meta.group(1))
            blueprint["detection_sources"]["theme_color"] = "Meta theme-color"

        # Apple touch icon & favicons
        icon_matches = re.findall(r'<link\s+[^>]*rel=["\'](apple-touch-icon(?:-precomposed)?|icon|shortcut icon)["\'][^>]*href=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
        if not icon_matches:
            icon_matches = re.findall(r'<link\s+[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\'](apple-touch-icon(?:-precomposed)?|icon|shortcut icon)["\']', html_text, re.IGNORECASE)
            icon_matches = [(rel, href) for (href, rel) in icon_matches]

        for rel, href in icon_matches:
            clean_href = href.split("?")[0].strip()
            target = base_dir / clean_href.lstrip("/")
            if target.exists() and target.is_file():
                blueprint["icon_path"] = str(target)
                blueprint["detection_sources"]["icon"] = f"HTML <link rel='{rel}'> ({target.name})"
                break

    @classmethod
    def _extract_from_html_remote(cls, html_text: str, base_url: str, blueprint: Dict[str, Any]):
        """Extracts metadata and icons from remote HTML."""
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", html_text, re.IGNORECASE)
        if title_match and title_match.group(1).strip():
            raw_title = title_match.group(1).strip().split("|")[0].split("-")[0].strip()
            if len(raw_title) >= 2:
                blueprint["app_name"] = cls.clean_app_name(raw_title)
                blueprint["bundle_id"] = cls.generate_bundle_id(raw_title)
                blueprint["detection_sources"]["app_name"] = "Remote HTML <title>"

        app_meta = re.search(r'<meta\s+name=["\'](apple-mobile-web-app-title|application-name)["\']\s+content=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
        if app_meta:
            blueprint["app_name"] = cls.clean_app_name(app_meta.group(2))

        theme_meta = re.search(r'<meta\s+name=["\']theme-color["\']\s+content=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
        if theme_meta:
            blueprint["theme_color"] = cls.normalize_hex_color(theme_meta.group(1))

        # Apple touch icon & favicons
        icon_matches = re.findall(r'<link\s+[^>]*rel=["\'](apple-touch-icon(?:-precomposed)?|icon|shortcut icon)["\'][^>]*href=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
        for rel, href in icon_matches:
            full_url = urllib.parse.urljoin(base_url, href)
            blueprint["icon_path"] = full_url
            blueprint["detection_sources"]["icon"] = f"Remote Apple Touch Icon ({rel})"
            break

        if not blueprint["icon_path"]:
            # Standard Apple fallback
            blueprint["icon_path"] = urllib.parse.urljoin(base_url, "/apple-touch-icon.png")

    @classmethod
    def _discover_local_icon(cls, dir_path: Path, manifest: Dict[str, Any]) -> Optional[Path]:
        """Discovers best logo from manifest or filesystem case-insensitively."""
        # 1. Manifest icons
        if manifest and manifest.get("icons"):
            icons = manifest["icons"]
            # Prioritize SVG
            for ico in icons:
                src = ico.get("src", "")
                if src.lower().endswith(".svg"):
                    cand = dir_path / src.lstrip("./\\")
                    if cand.exists() and cand.is_file():
                        return cand
                    matches = list(dir_path.glob(f"**/{Path(src).name}"))
                    if matches:
                        return matches[0]

            # Highest resolution icon from manifest
            best_size = 0
            best_path = None
            for ico in icons:
                src = ico.get("src", "")
                sizes = ico.get("sizes", "0x0")
                match = re.search(r"(\d+)x\1", sizes)
                sz = int(match.group(1)) if match else 0
                cand = dir_path / src.lstrip("./\\")
                if cand.exists() and cand.is_file() and sz >= best_size:
                    best_size = sz
                    best_path = cand
                else:
                    matches = list(dir_path.glob(f"**/{Path(src).name}"))
                    if matches and sz >= best_size:
                        best_size = sz
                        best_path = matches[0]
            if best_path:
                return best_path

        # Gather all image files case-insensitively, excluding build artifacts
        all_image_files: List[Path] = []
        for f in dir_path.glob("**/*"):
            if f.is_file() and f.suffix.lower() in cls.SUPPORTED_ICON_EXTS:
                parts = f.relative_to(dir_path).parts
                if any(p.startswith(".") or p in ["node_modules", ".git", ".venv", "__pycache__"] for p in parts):
                    continue
                all_image_files.append(f)

        # 2. Priority filenames (checked case-insensitively)
        priority_names = [
            "apple-touch-icon.png",
            "apple-touch-icon-precomposed.png",
            "icon-1024.png",
            "icon-512.png",
            "icon-192.png",
            "logo.svg",
            "icon.svg",
            "app_icon.svg",
            "app-icon.svg",
            "brand.svg",
            "logo.png",
            "icon.png",
            "app_icon.png",
            "app-icon.png",
            "brand.png",
            "app.png",
            "logo.webp",
            "icon.webp",
            "logo.jpg",
            "logo.jpeg",
            "icon.jpg",
            "favicon.svg",
            "favicon.png",
            "favicon.ico"
        ]

        for pname in priority_names:
            for f in all_image_files:
                if f.name.lower() == pname.lower():
                    return f

        # 3. Keyword matching in stem, prioritizing root / asset folders
        def score_file(p: Path) -> int:
            stem = p.stem.lower()
            score = 0
            if "apple-touch" in stem:
                score += 50
            elif "logo" in stem:
                score += 40
            elif "app_icon" in stem or "app-icon" in stem:
                score += 35
            elif "brand" in stem:
                score += 30
            elif "icon" in stem:
                score += 25
            # SVG bonus for infinite scalability
            if p.suffix.lower() == ".svg":
                score += 15
            # Depth penalty: shallower files get higher score
            score -= len(p.relative_to(dir_path).parts) * 2
            return score

        keyword_matches = [
            f for f in all_image_files
            if any(k in f.stem.lower() for k in ["logo", "icon", "brand", "touch", "appicon"])
        ]
        if keyword_matches:
            keyword_matches.sort(key=score_file, reverse=True)
            return keyword_matches[0]

        return None

    @classmethod
    def _detect_ios_permissions(cls, dir_path: Path) -> Dict[str, str]:
        """Scans JS/HTML for Web APIs and returns required Apple Privacy Keys & Descriptions."""
        perms = {}
        patterns = {
            "NSCameraUsageDescription": (
                [r"navigator\.mediaDevices\.getUserMedia", r"capture=['\"]camera['\"]", r"video:\s*true"],
                "This app requires access to the camera for capturing photos and videos."
            ),
            "NSMicrophoneUsageDescription": (
                [r"audio:\s*true", r"AudioContext", r"webkitAudioContext", r"navigator\.mediaDevices\.getUserMedia"],
                "This app requires access to the microphone for audio recording and voice interaction."
            ),
            "NSLocationWhenInUseUsageDescription": (
                [r"navigator\.geolocation\.getCurrentPosition", r"navigator\.geolocation\.watchPosition"],
                "This app requires access to your location to provide personalized, location-based services."
            ),
            "NSPhotoLibraryAddUsageDescription": (
                [r"toDataURL", r"canvas\.toBlob", r"download=", r"saveImage"],
                "This app requires access to save downloaded photos directly to your Photo Library."
            ),
            "NSMotionUsageDescription": (
                [r"DeviceOrientationEvent", r"DeviceMotionEvent"],
                "This app requires access to device motion and gyro sensors for interactive controls."
            )
        }

        # Scan all .js, .ts, .html, .vue, .jsx, .tsx files
        scan_exts = {".html", ".htm", ".js", ".mjs", ".ts", ".jsx", ".tsx", ".vue"}
        for f in dir_path.glob("**/*"):
            if f.is_file() and f.suffix.lower() in scan_exts and f.stat().st_size < 1_000_000:
                try:
                    text = f.read_text(encoding="utf-8", errors="ignore")
                    for perm_key, (reg_list, desc) in patterns.items():
                        if perm_key not in perms:
                            for reg in reg_list:
                                if re.search(reg, text, re.IGNORECASE):
                                    perms[perm_key] = desc
                                    break
                except Exception:
                    pass

        return perms

    # --------------------------------------------------------------------------
    # FORMATTING UTILITIES
    # --------------------------------------------------------------------------

    @classmethod
    def clean_app_name(cls, name: str) -> str:
        """Cleans and formats app display name."""
        cleaned = re.sub(r"[_\-.]+", " ", name).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.title() or "Web App"

    @classmethod
    def generate_bundle_id(cls, name: str) -> str:
        """Generates valid Apple reverse-domain bundle ID: com.web2ipa.<slug>."""
        slug = re.sub(r"[^a-zA-Z0-9]", "", name.lower())
        if not slug:
            slug = "app"
        return f"com.web2ipa.{slug[:30]}"

    @classmethod
    def normalize_hex_color(cls, color_str: str) -> str:
        """Ensures valid 6-digit hex color with leading '#'."""
        c = str(color_str).strip()
        if not c.startswith("#") and len(c) in [3, 6]:
            c = f"#{c}"
        if re.match(r"^#[0-9a-fA-F]{6}$", c):
            return c
        if re.match(r"^#[0-9a-fA-F]{3}$", c):
            return f"#{c[1]*2}{c[2]*2}{c[3]*2}"
        return "#0f172a"
