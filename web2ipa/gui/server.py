import os
import sys
import re
import shutil
import tempfile
import zipfile
import subprocess
import base64
import urllib.parse
import mimetypes
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from ..builder import IPABuilder, OUTPUT_DIR
from ..qr_server import QRServer
from ..evolution import EvolutionEngine
from ..ai_advisor import GeminiAdvisor
from ..app_inspector import iOSAppInspector
from ..icon_generator import iOSIconGenerator
from ..security import VulnerabilityScanner
from ..mobile_access import MobileAccessManager

app = FastAPI(title="Web2IPA AI Studio")

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent
if (PROJECT_ROOT / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(PROJECT_ROOT / "assets")), name="assets")

STATIC_DIR = BASE_DIR / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/growth")
async def get_growth():
    memory = EvolutionEngine.load_memory()
    memory["gemini_available"] = GeminiAdvisor.is_available()
    memory["active_model"] = GeminiAdvisor.get_latest_flash_model()
    memory["model_preference"] = GeminiAdvisor.get_configured_model_preference()
    return JSONResponse(memory)

@app.get("/api/models")
async def get_models():
    models = GeminiAdvisor.discover_available_models(force_refresh=False)
    pref = GeminiAdvisor.get_configured_model_preference()
    latest = GeminiAdvisor.get_latest_flash_model()
    return JSONResponse({
        "models": models,
        "preference": pref,
        "latest_model": latest,
        "is_available": GeminiAdvisor.is_available(),
        "is_online": GeminiAdvisor.is_online()
    })

@app.post("/api/set-model")
async def set_model(model_name: str = Form(...)):
    ok = GeminiAdvisor.set_model_preference(model_name)
    return JSONResponse({"success": ok, "model": model_name})

@app.post("/api/security-audit")
async def security_audit(code_snippet: Optional[str] = Form(None), path: Optional[str] = Form(None)):
    if path and Path(path).exists():
        report = VulnerabilityScanner.audit_directory(Path(path))
        return JSONResponse({"success": True, "report": report})
    elif code_snippet:
        findings = VulnerabilityScanner.audit_code_snippet(code_snippet)
        score = 100 - (sum(15 if f["severity"] == "CRITICAL" else 10 if f["severity"] == "HIGH" else 5 for f in findings))
        score = max(0, min(100, score))
        grade = "A+" if score >= 95 else "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 50 else "F"
        return JSONResponse({"success": True, "report": {
            "score": score,
            "grade": grade,
            "findings": findings,
            "total_issues": len(findings)
        }})
    return JSONResponse({"success": False, "error": "No valid path or code provided"})

@app.post("/api/surprise-me")
async def surprise_me(
    app_name: str = Form("iOS App"),
    html_snippet: Optional[str] = Form(""),
    framework: Optional[str] = Form("Vanilla HTML5 / Modern JS")
):
    res = EvolutionEngine.generate_surprise_innovations(
        app_name=app_name,
        html_snippet=html_snippet or "",
        framework=framework or "Vanilla HTML5 / Modern JS"
    )
    return JSONResponse(res)

@app.get("/api/innovations")
async def get_innovations():
    innovations = EvolutionEngine.load_innovations()
    return JSONResponse({"innovations": innovations})

@app.post("/api/gemini-analyze")
async def gemini_analyze(code_snippet: str = Form(...), app_name: str = Form("iOS App")):
    res = GeminiAdvisor.analyze_and_optimize_code(code_snippet, app_name)
    return JSONResponse(res)

@app.post("/api/gemini-store-copy")
async def gemini_store_copy(app_name: str = Form(...), url: Optional[str] = Form(None), description: Optional[str] = Form(None)):
    res = GeminiAdvisor.generate_app_store_metadata(app_name, url, description)
    return JSONResponse(res)

@app.post("/api/inspect")
async def inspect_source_api(
    mode: str = Form("url"),
    url: Optional[str] = Form(None),
    path: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    try:
        if mode == "url":
            if not url:
                return JSONResponse({"success": False, "error": "URL is required"})
            blueprint = iOSAppInspector.inspect_url(url)
        elif mode == "zip":
            if not file:
                return JSONResponse({"success": False, "error": "ZIP file is required"})
            temp_dir = Path(tempfile.mkdtemp(prefix="web2ipa_upload_"))
            zip_path = temp_dir / file.filename
            with open(zip_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            blueprint = iOSAppInspector.inspect_zip(zip_path)
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
        elif mode == "folder":
            if not path or not os.path.exists(path):
                return JSONResponse({"success": False, "error": "Folder path is invalid or does not exist"})
            blueprint = iOSAppInspector.inspect_directory(Path(path))
        else:
            return JSONResponse({"success": False, "error": f"Invalid mode: {mode}"})

        blueprint["success"] = True
        blueprint["local_logo_path"] = blueprint.get("icon_path")
        blueprint["logo_base64"] = blueprint.get("icon_base64")
        blueprint["icon_source"] = blueprint.get("detection_sources", {}).get("icon", "Default")
        return JSONResponse(blueprint)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.get("/api/mobile-access")
async def get_mobile_access():
    mgr = MobileAccessManager.get_instance()
    telemetry = mgr.get_telemetry()
    return JSONResponse(telemetry)

@app.post("/api/mobile-access/start-tunnel")
async def start_mobile_tunnel():
    mgr = MobileAccessManager.get_instance()
    mgr.start_tunnel()
    telemetry = mgr.get_telemetry()
    return JSONResponse(telemetry)

@app.post("/api/mobile-access/stop-tunnel")
async def stop_mobile_tunnel():
    mgr = MobileAccessManager.get_instance()
    mgr.stop_tunnel()
    telemetry = mgr.get_telemetry()
    return JSONResponse(telemetry)

@app.post("/api/inspect-url")
async def inspect_url_api(url: str = Form(...)):
    try:
        blueprint = iOSAppInspector.inspect_url(url)
        blueprint["success"] = True
        blueprint["local_logo_path"] = blueprint.get("icon_path")
        blueprint["logo_base64"] = blueprint.get("icon_base64")
        blueprint["icon_source"] = blueprint.get("detection_sources", {}).get("icon", "Remote Apple Touch Icon")
        return JSONResponse(blueprint)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.post("/api/upload-icon")
async def upload_icon_api(icon_file: UploadFile = File(...), app_name: Optional[str] = Form("iOS App")):
    """Uploads, validates, and normalizes a custom app icon / logo picture."""
    try:
        if not icon_file.filename:
            return JSONResponse({"success": False, "error": "No file uploaded"})

        allowed_exts = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".ico"}
        ext = Path(icon_file.filename).suffix.lower()
        if ext not in allowed_exts:
            return JSONResponse({"success": False, "error": f"Unsupported format '{ext}'. Please upload PNG, JPG, SVG, WebP, or ICO."})

        temp_dir = Path(tempfile.mkdtemp(prefix="web2ipa_icon_up_"))
        temp_file = temp_dir / icon_file.filename
        with open(temp_file, "wb") as f:
            shutil.copyfileobj(icon_file.file, f)

        cached_path, b64_str = iOSIconGenerator.cache_normalized_icon(str(temp_file), app_name or "iOS App")

        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass

        if not cached_path or not b64_str:
            return JSONResponse({"success": False, "error": "Failed to process and normalize icon image"})

        return JSONResponse({
            "success": True,
            "icon_path": str(cached_path),
            "icon_base64": b64_str,
            "filename": icon_file.filename
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.get("/open-output")
async def open_output_dir():
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["xdg-open", str(OUTPUT_DIR)])
        return JSONResponse({"success": True, "path": str(OUTPUT_DIR)})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.get("/download/{filename}")
async def download_page(filename: str, request: Request, raw: Optional[int] = 0):
    clean_name = urllib.parse.unquote(filename)
    file_path = OUTPUT_DIR / clean_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    accept = request.headers.get("accept", "").lower()
    user_agent = request.headers.get("user-agent", "").lower()
    
    if raw == 1 or "application/octet-stream" in accept or "curl" in user_agent or "wget" in user_agent:
        media = "application/octet-stream"
        disposition = "attachment"
        if clean_name.endswith(".zip"):
            media = "application/zip"
        elif clean_name.endswith(".mobileconfig"):
            media = "application/x-apple-aspen-config"
            disposition = "attachment"
        return FileResponse(path=file_path, filename=clean_name, media_type=media, content_disposition_type=disposition)

    # Return Cupertino mobile install landing page
    size_mb = round(file_path.stat().st_size / (1024 * 1024), 2)
    html_page = QRServer.generate_landing_page_html(clean_name, size_mb)
    return HTMLResponse(content=html_page)

@app.get("/install-profile/{filename}")
async def install_profile_file(filename: str, request: Request):
    clean_name = urllib.parse.unquote(filename)
    file_path = OUTPUT_DIR / clean_name
    if not file_path.exists():
        stem = Path(clean_name).stem
        ext = Path(clean_name).suffix
        base_stem = re.sub(r'(-v[0-9.]+(-XcodeProject)?)?$', '', stem)
        candidates = list(OUTPUT_DIR.glob(f"{base_stem}*{ext}"))
        if candidates:
            candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            file_path = candidates[0]
            clean_name = file_path.name
        else:
            raise HTTPException(status_code=404, detail="Profile not found")

    # CRITICAL: application/x-apple-aspen-config with attachment disposition.
    # Tells Safari to treat the profile as a system configuration handoff ("Profile Downloaded").
    # If served as inline, Safari attempts to render the XML in the browser window, showing "Unable to preview".
    return FileResponse(
        path=file_path,
        filename=clean_name,
        media_type="application/x-apple-aspen-config",
        content_disposition_type="attachment"
    )

@app.get("/download-raw/{filename}")
async def download_raw_file(filename: str):
    clean_name = urllib.parse.unquote(filename)
    file_path = OUTPUT_DIR / clean_name
    if not file_path.exists():
        stem = Path(clean_name).stem
        ext = Path(clean_name).suffix
        is_xcode_req = "xcodeproject" in stem.lower()
        base_prefix = re.sub(r'(-v[0-9.]+)?(-XcodeProject)?$', '', stem, flags=re.IGNORECASE)
        candidates = list(OUTPUT_DIR.glob(f"{base_prefix}*{ext}"))
        if is_xcode_req:
            candidates = [c for c in candidates if "xcodeproject" in c.name.lower()] or candidates
        if candidates:
            candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            file_path = candidates[0]
            clean_name = file_path.name
        else:
            raise HTTPException(status_code=404, detail="File not found")

    media = "application/octet-stream"
    disposition = "attachment"
    if clean_name.endswith(".zip"):
        media = "application/zip"
    elif clean_name.endswith(".mobileconfig"):
        media = "application/x-apple-aspen-config"

    return FileResponse(path=file_path, filename=clean_name, media_type=media, content_disposition_type=disposition)

@app.get("/app/{slug}")
@app.get("/app/{slug}/")
@app.get("/app/{slug}/{sub_path:path}")
async def serve_app_assets(slug: str, sub_path: str = ""):
    clean_slug = urllib.parse.unquote(slug)
    app_dir = (OUTPUT_DIR / "apps" / clean_slug).resolve()
    if not app_dir.exists() or not app_dir.is_dir():
        raise HTTPException(status_code=404, detail="Web application not found")

    rel_path = sub_path.strip("/") if sub_path and sub_path.strip("/") else "index.html"
    target_file = (app_dir / rel_path).resolve()

    # Prevent directory traversal
    if not str(target_file).startswith(str(app_dir)):
        raise HTTPException(status_code=403, detail="Access denied")

    if target_file.is_dir():
        target_file = (target_file / "index.html").resolve()

    if not target_file.exists():
        fallback_index = app_dir / "index.html"
        if fallback_index.exists():
            target_file = fallback_index
        else:
            raise HTTPException(status_code=404, detail="Asset not found")

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

    return FileResponse(
        path=target_file,
        filename=target_file.name,
        media_type=content_type,
        content_disposition_type="inline",
        headers={"X-Frame-Options": "ALLOWALL", "Access-Control-Allow-Origin": "*"}
    )

@app.get("/api/qr-code")
async def get_qr_code(url: str):
    try:
        qr_b64 = QRServer.generate_qr_base64(url)
        return JSONResponse({"success": True, "qr_code_base64": qr_b64})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.post("/api/build")
async def api_build(
    request: Request,
    mode: str = Form(...),
    app_name: str = Form("iOS App"),
    bundle_id: str = Form("com.web2ipa.app"),
    version_name: str = Form("1.0.0"),
    screen_orientation: str = Form("sensor"),
    is_fullscreen: str = Form("true"),
    theme_color: Optional[str] = Form("#000000"),
    permissions: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    auto_logo_path: Optional[str] = Form(None),
    custom_icon_path: Optional[str] = Form(None),
    path: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    custom_icon: Optional[UploadFile] = File(None)
):
    fullscreen_bool = is_fullscreen.lower() == "true"
    builder = IPABuilder()

    extra_perms = [p.strip() for p in permissions.split(",") if p.strip()] if permissions else None

    icon_override_path = None
    if custom_icon and custom_icon.filename:
        icon_cache_dir = Path.home() / ".web2ipa" / "icons"
        icon_cache_dir.mkdir(parents=True, exist_ok=True)
        temp_icon_file = icon_cache_dir / f"upload_{custom_icon.filename}"
        with open(temp_icon_file, "wb") as ib:
            shutil.copyfileobj(custom_icon.file, ib)
        norm_path, _ = iOSIconGenerator.cache_normalized_icon(str(temp_icon_file), app_name or "iOS App")
        icon_override_path = str(norm_path or temp_icon_file)
    elif custom_icon_path and os.path.exists(custom_icon_path):
        icon_override_path = custom_icon_path
    elif auto_logo_path and os.path.exists(auto_logo_path):
        icon_override_path = auto_logo_path

    if mode == "url":
        if not url:
            return JSONResponse({"success": False, "error": "URL is required"})
        result = builder.build_from_url(
            url=url,
            app_name=app_name,
            bundle_id=bundle_id,
            version_name=version_name,
            is_fullscreen=fullscreen_bool,
            screen_orientation=screen_orientation,
            icon_path=icon_override_path,
            theme_color=theme_color,
            extra_permissions=extra_perms
        )
    elif mode == "folder":
        folder_dir = path
        if not folder_dir or not os.path.exists(folder_dir):
            return JSONResponse({"success": False, "error": f"Folder directory '{folder_dir}' does not exist"})
        result = builder.build_from_directory(
            source_dir=str(folder_dir),
            app_name=app_name,
            bundle_id=bundle_id,
            version_name=version_name,
            is_fullscreen=fullscreen_bool,
            screen_orientation=screen_orientation,
            icon_path=icon_override_path,
            theme_color=theme_color,
            extra_permissions=extra_perms
        )
    elif mode == "zip":
        if not file:
            return JSONResponse({"success": False, "error": "ZIP file is required"})
        
        temp_dir = Path(tempfile.mkdtemp(prefix="web2ipa_upload_"))
        zip_path = temp_dir / file.filename
        
        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        extract_dir = temp_dir / "extracted"
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        html_files = list(extract_dir.glob("**/*.html"))
        source_dir = html_files[0].parent if html_files else extract_dir

        result = builder.build_from_directory(
            source_dir=str(source_dir),
            app_name=app_name,
            bundle_id=bundle_id,
            version_name=version_name,
            is_fullscreen=fullscreen_bool,
            screen_orientation=screen_orientation,
            icon_path=icon_override_path,
            theme_color=theme_color,
            extra_permissions=extra_perms
        )

        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
    else:
        return JSONResponse({"success": False, "error": f"Invalid mode: {mode}"})

    if result.get("success"):
        ipa_name = result["ipa_name"]
        host_header = request.headers.get("host", "")
        if not host_header or "localhost" in host_header or "127.0.0.1" in host_header:
            req_port = int(host_header.split(":")[-1]) if ":" in host_header else 8992
            dl_url = QRServer.get_download_url(ipa_name, port=req_port)
        else:
            scheme = request.url.scheme or "http"
            dl_url = f"{scheme}://{host_header}/download/{ipa_name}"

        qr_b64 = QRServer.generate_qr_base64(dl_url)
        sanitized_slug = result.get("slug") or re.sub(r'[^a-zA-Z0-9_-]', '_', result.get("app_name", "App")).strip('_') or "iOSApp"
        result["slug"] = sanitized_slug
        result["download_url"] = dl_url
        result["qr_code_base64"] = qr_b64
        result["ipa_download_url"] = f"/download-raw/{urllib.parse.quote(result['ipa_name'])}"
        result["profile_download_url"] = f"/install-profile/{urllib.parse.quote(result['mobileconfig_name'])}"
        result["zip_download_url"] = f"/download-raw/{urllib.parse.quote(result['xcodeproj_zip_name'])}"
        result["app_preview_url"] = f"/app/{urllib.parse.quote(sanitized_slug)}/index.html"

    return JSONResponse(result)

def start_server(port: int = 8992, auto_open: bool = True):
    import uvicorn
    import webbrowser
    import threading
    import time

    def open_browser():
        time.sleep(1.2)
        try:
            webbrowser.open(f"http://localhost:{port}")
        except Exception:
            pass

    if auto_open:
        threading.Thread(target=open_browser, daemon=True).start()

    print(f"🍏 Web2IPA AI Studio running at http://localhost:{port}")

    # Initialize Mobile Access Manager & start Cloudflare Quick Tunnel in background
    mobile_mgr = MobileAccessManager.get_instance(port=port)
    def init_mobile():
        mobile_mgr.start_tunnel()
        mobile_mgr.print_terminal_banner()

    threading.Thread(target=init_mobile, daemon=True).start()

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
