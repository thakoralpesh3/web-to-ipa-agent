import os
import io
import re
import sys
import time
import shutil
import zipfile
import hashlib
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List

from .app_inspector import iOSAppInspector
from .code_patcher import iOSCodePatcher
from .icon_generator import iOSIconGenerator
from .template_engine import TemplateEngine
from .self_healer import iOSSelfHealer
from .evolution import EvolutionEngine
from .checkpoint import CheckpointManager
from .optimizer import AssetOptimizer
from .security import VulnerabilityScanner, InputSanitizer, SSRFProtector
from .pwa_synthesizer import PWASynthesizer
from .ipa_packager import IPAPackager
from .qr_server import QRServer

OUTPUT_DIR = Path.home() / "Web2IPA_Output"
PERSISTENT_WORKSPACES_DIR = Path.home() / ".web2ipa" / "workspaces"

class IPABuilder:
    """
    Autonomous Builder for iOS:
    Converts any web project directory, ZIP, or live URL into:
      1. Native Swift / WKWebView Xcode Project (.xcodeproj.zip)
      2. Standalone iOS Application Bundle (.ipa) for AltStore / Sideloadly / TrollStore
      3. 1-Tap iOS WebClip Configuration Profile (.mobileconfig) for instant Safari install
    """

    def __init__(self, log_callback: Optional[Callable[[str, int], None]] = None):
        self.log_callback = log_callback or (lambda msg, pct: print(f"[{pct}%] {msg}"))

    def log(self, message: str, percent: int = 0):
        self.log_callback(message, percent)

    def build_from_directory(
        self,
        source_dir: str,
        app_name: str = "iOS App",
        bundle_id: str = "com.web2ipa.app",
        version_name: str = "1.0.0",
        version_code: int = 1,
        is_fullscreen: bool = True,
        screen_orientation: str = "sensor",
        icon_path: Optional[str] = None,
        remote_url: Optional[str] = None,
        theme_color: str = "#000000",
        extra_permissions: Optional[List[str]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        PERSISTENT_WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)

        clean_bundle_id = InputSanitizer.sanitize_bundle_id(bundle_id)
        clean_app_name = InputSanitizer.sanitize_app_name(app_name)
        sanitized_slug = re.sub(r'[^a-zA-Z0-9_-]', '_', clean_app_name)

        if not session_id:
            session_id = hashlib.md5(f"{source_dir}_{clean_app_name}_{clean_bundle_id}_{version_name}".encode()).hexdigest()[:12]

        workspace_dir = PERSISTENT_WORKSPACES_DIR / f"ws_{session_id}"
        assets_staging = workspace_dir / "staging_assets"
        project_dir = workspace_dir / "xcode_project"

        checkpoint = CheckpointManager.init_checkpoint(
            session_id=session_id,
            params={
                "source_dir": str(source_dir),
                "app_name": clean_app_name,
                "bundle_id": clean_bundle_id,
                "version_name": version_name,
                "version_code": version_code,
                "is_fullscreen": is_fullscreen,
                "orientation": screen_orientation,
                "remote_url": remote_url,
                "theme_color": theme_color
            },
            workspace_dir=str(workspace_dir)
        )

        current_stage = checkpoint.get("stage", "INIT")
        self.log(f"🍎 Initializing Web-to-iOS build for '{clean_app_name}' (Session: {session_id})...", 5)

        # Autodetect logo if not explicitly provided
        effective_icon_path = icon_path
        if not effective_icon_path or not Path(effective_icon_path).exists():
            try:
                blueprint = iOSAppInspector.inspect_directory(Path(source_dir))
                if blueprint.get("icon_path") and Path(blueprint["icon_path"]).exists():
                    effective_icon_path = blueprint["icon_path"]
                    self.log(f"🎨 Auto-detected project logo: {Path(effective_icon_path).name}", 10)
            except Exception:
                pass

        # Stage 1: Staging Source
        if current_stage in ["INIT"] or not assets_staging.exists():
            workspace_dir.mkdir(parents=True, exist_ok=True)
            if assets_staging.exists():
                shutil.rmtree(assets_staging)
            shutil.copytree(source_dir, assets_staging)
            current_stage = "STAGED"
            CheckpointManager.commit_stage(session_id, "STAGED")

        # Stage 2: AI Framework Identification & Self-Healing
        framework = checkpoint.get("framework", "")
        repairs = checkpoint.get("repairs_made", [])
        permissions = checkpoint.get("detected_permissions", [])

        if current_stage in ["STAGED"] or not framework:
            framework = EvolutionEngine.identify_framework(assets_staging)
            self.log(f"🧠 Detected Web Architecture: [bold cyan]{framework}[/bold cyan]", 15)

            self.log("🛡️ Running iOS Self-Healer (patching 100vh, Dynamic Island insets, Web Audio unlock)...", 20)
            heal_res = iOSSelfHealer.diagnose_and_heal_directory(assets_staging)
            repairs = heal_res.get("repairs_made", [])
            permissions = heal_res.get("detected_permissions", [])
            if extra_permissions:
                permissions = list(dict.fromkeys(permissions + extra_permissions))
            for rep in repairs:
                self.log(f"  ⚡ Auto-Repaired: {rep}", 25)

            current_stage = "SELF_HEALED"
            CheckpointManager.commit_stage(session_id, "SELF_HEALED", {
                "framework": framework,
                "repairs_made": repairs,
                "detected_permissions": permissions
            })
        else:
            if extra_permissions:
                permissions = list(dict.fromkeys(permissions + extra_permissions))
            self.log(f"⚡ [Auto-Resume] Resuming session {session_id} (Skipping Staging & Healing: {framework})...", 25)

        # Stage 2.5: Cyber Defense SAST Security Audit
        audit_report = VulnerabilityScanner.audit_directory(assets_staging)
        self.log(f"🛡️ Cyber Defense Audit: Score {audit_report['score']}/100 (Grade: {audit_report['grade']}) | {audit_report['total_issues']} Vulnerabilities Analyzed & Shielded", 30)

        # Stage 3: Code Patching, Safe Area Insets & Cyber Hardening
        if current_stage in ["SELF_HEALED"]:
            self.log("🔧 Patching Viewports, Dynamic Island Safe Areas & WebKit Native Bridge...", 35)
            patch_res = iOSCodePatcher.patch_html_directory(
                str(assets_staging),
                enable_haptics=True,
                enable_notch_css=True,
                app_title=clean_app_name
            )

            # Stage 3.5: Turbo Asset Optimizer & Minifier
            opt_res = AssetOptimizer.optimize_directory(assets_staging)
            if opt_res["saved_kb"] > 0:
                self.log(f"⚡ Turbo Minifier: Saved {opt_res['saved_kb']} KB ({opt_res['percent_saved']}%) payload size.", 45)

            # Stage 3.6: Autonomous PWA & Offline Service Worker Synthesizer
            pwa_res = PWASynthesizer.synthesize_pwa_assets(
                assets_staging,
                app_name=clean_app_name,
                theme_color=theme_color,
                is_landscape=(screen_orientation == "landscape")
            )
            if pwa_res.get("success"):
                self.log("📴 PWA Synthesizer: Injected persistent CacheStorage Service Worker & Web Manifest.", 50)

            current_stage = "CODE_PATCHED"
            CheckpointManager.commit_stage(session_id, "CODE_PATCHED")

        # Stage 4: Native Swift / Xcode Project Generation
        if current_stage in ["CODE_PATCHED"] or not project_dir.exists():
            self.log("📱 Generating Native Swift / WKWebView Xcode Project with Offline Resilience...", 55)
            TemplateEngine.generate_project(
                target_dir=str(project_dir),
                app_name=clean_app_name,
                bundle_id=clean_bundle_id,
                version_name=version_name,
                version_code=version_code,
                remote_url=remote_url,
                is_fullscreen=is_fullscreen,
                screen_orientation=screen_orientation,
                theme_color=theme_color,
                extra_permissions=permissions,
                custom_icon_path=effective_icon_path
            )

            # Copy web assets to app's www/ folder
            clean_slug = re.sub(r'[^a-zA-Z0-9]', '', clean_app_name) or "App"
            target_www = project_dir / clean_slug / "www"
            target_www.mkdir(parents=True, exist_ok=True)
            shutil.copytree(assets_staging, target_www, dirs_exist_ok=True)

            current_stage = "PROJECT_GENERATED"
            CheckpointManager.commit_stage(session_id, "PROJECT_GENERATED")

        # Stage 5: App Icon Generation & Apple Asset Catalog
        self.log("🎨 Generating Apple AppIcon Catalog (all 1x/2x/3x sizes + 1024x1024 App Store icon)...", 70)
        icons_dir = workspace_dir / "icons"
        icons_dir.mkdir(parents=True, exist_ok=True)
        iOSIconGenerator.generate_apple_icon_catalog(
            output_dir=icons_dir,
            source_icon_path=effective_icon_path,
            app_name=clean_app_name,
            theme_color=theme_color
        )

        # WebClip profiles are best served with a 180x180 Retina icon (AppIcon-60@3x.png)
        webclip_icon = icons_dir / "AppIcon-60@3x.png"
        if not webclip_icon.exists():
            webclip_icon = icons_dir / "AppIcon-1024.png"
        icon_for_profile = str(webclip_icon) if webclip_icon.exists() else effective_icon_path

        # Stage 6: Packaging Outputs (Xcode ZIP, Standalone IPA, 1-Tap .mobileconfig)
        self.log("📦 Packaging Triple iOS Deliverables (.xcodeproj.zip, .ipa, .mobileconfig)...", 85)

        # 6a. Preserve Staged Web Assets in persistent OUTPUT_DIR / apps / sanitized_slug /
        app_assets_dest = OUTPUT_DIR / "apps" / sanitized_slug
        app_assets_dest.mkdir(parents=True, exist_ok=True)
        shutil.copytree(assets_staging, app_assets_dest, dirs_exist_ok=True)

        # Determine real LAN IP so iPhones on Wi-Fi can load the app directly
        lan_ip = QRServer.get_local_ip()
        app_port = 8992
        if remote_url:
            target_web_url = remote_url
        else:
            target_web_url = f"http://{lan_ip}:{app_port}/app/{sanitized_slug}/index.html"

        # 6b. Zip Xcode Project
        out_zip_name = f"{sanitized_slug}-v{version_name}-XcodeProject.zip"
        final_zip_path = OUTPUT_DIR / out_zip_name
        TemplateEngine.zip_project(project_dir, final_zip_path)

        # 6c. Standalone .ipa Bundle
        out_ipa_name = f"{sanitized_slug}-v{version_name}.ipa"
        final_ipa_path = OUTPUT_DIR / out_ipa_name
        IPAPackager.package_ipa(
            output_ipa_path=final_ipa_path,
            app_name=clean_app_name,
            bundle_id=clean_bundle_id,
            version_name=version_name,
            version_code=version_code,
            web_assets_dir=assets_staging,
            icon_source_dir=icons_dir,
            remote_url=remote_url,
            is_fullscreen=is_fullscreen,
            permissions=permissions
        )

        # 6d. 1-Tap iOS WebClip Profile (.mobileconfig)
        out_mobileconfig_name = f"{sanitized_slug}.mobileconfig"
        final_mobileconfig_path = OUTPUT_DIR / out_mobileconfig_name
        IPAPackager.generate_mobileconfig(
            output_path=final_mobileconfig_path,
            app_name=clean_app_name,
            target_url=target_web_url,
            icon_png_path=icon_for_profile,
            bundle_id=clean_bundle_id
        )

        # 6e. OTA Manifest (manifest.plist)
        out_manifest_name = f"{sanitized_slug}-manifest.plist"
        final_manifest_path = OUTPUT_DIR / out_manifest_name
        IPAPackager.generate_ota_manifest(
            output_path=final_manifest_path,
            ipa_download_url=f"http://{lan_ip}:{app_port}/download-raw/{out_ipa_name}",
            bundle_id=clean_bundle_id,
            app_name=clean_app_name,
            version_name=version_name
        )

        CheckpointManager.commit_stage(session_id, "COMPLETED")
        CheckpointManager.remove_checkpoint(session_id)

        try:
            shutil.rmtree(workspace_dir)
        except Exception:
            pass

        ipa_size_mb = final_ipa_path.stat().st_size / (1024 * 1024) if final_ipa_path.exists() else 0.0

        growth_data = EvolutionEngine.record_build(
            app_name=clean_app_name,
            framework=framework,
            success=True,
            repairs=repairs,
            permissions=permissions,
            ipa_size_mb=round(ipa_size_mb, 2)
        )

        self.log(f"🌱 Evolution Level: {growth_data['level']} ({growth_data['rank']}) | Total Exp: {growth_data['xp']} XP", 98)
        self.log(f"🎉 Build Successful! Generated: {out_ipa_name}, {out_mobileconfig_name}, and {out_zip_name}", 100)

        return {
            "success": True,
            "ipa_path": str(final_ipa_path),
            "ipa_name": out_ipa_name,
            "ipa_size_mb": round(ipa_size_mb, 2),
            "mobileconfig_path": str(final_mobileconfig_path),
            "mobileconfig_name": out_mobileconfig_name,
            "xcodeproj_zip_path": str(final_zip_path),
            "xcodeproj_zip_name": out_zip_name,
            "manifest_path": str(final_manifest_path),
            "manifest_name": out_manifest_name,
            "target_web_url": target_web_url,
            "app_name": clean_app_name,
            "slug": sanitized_slug,
            "bundle_id": clean_bundle_id,
            "framework": framework,
            "repairs": repairs,
            "permissions": permissions,
            "evolution": growth_data
        }

    def build_from_url(
        self,
        url: str,
        app_name: Optional[str] = None,
        bundle_id: Optional[str] = None,
        version_name: str = "1.0.0",
        version_code: int = 1,
        is_fullscreen: bool = True,
        screen_orientation: str = "sensor",
        icon_path: Optional[str] = None,
        theme_color: Optional[str] = None,
        extra_permissions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        self.log(f"🔍 Deeply Inspecting iOS target URL: {url}...", 10)
        blueprint = iOSAppInspector.inspect_url(url)

        final_app_name = app_name or blueprint.get("app_name") or "iOS App"
        final_bundle_id = bundle_id or blueprint.get("bundle_id") or "com.web2ipa.app"
        final_theme_color = theme_color or blueprint.get("theme_color") or "#000000"
        final_icon_path = icon_path or blueprint.get("icon_path")

        detected_perms = list(blueprint.get("ios_permissions", {}).keys())
        if extra_permissions:
            detected_perms = list(dict.fromkeys(detected_perms + extra_permissions))

        temp_dir = Path(tempfile.mkdtemp(prefix="web2ipa_url_stage_"))
        index_html = temp_dir / "index.html"
        index_html.write_text(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>{final_app_name}</title>
    <script>
        window.location.replace("{url}");
    </script>
</head>
<body style="background-color: {final_theme_color}; margin: 0; padding: 0;"></body>
</html>
""", encoding="utf-8")

        try:
            return self.build_from_directory(
                source_dir=str(temp_dir),
                app_name=final_app_name,
                bundle_id=final_bundle_id,
                version_name=version_name,
                version_code=version_code,
                is_fullscreen=is_fullscreen,
                screen_orientation=screen_orientation,
                icon_path=final_icon_path,
                remote_url=url,
                theme_color=final_theme_color,
                extra_permissions=detected_perms
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
