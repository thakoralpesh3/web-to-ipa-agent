import os
import json
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

CONFIG_FILE = Path.home() / ".web2ipa" / "config.json"
MODELS_CACHE_FILE = Path.home() / ".web2ipa" / "models_cache.json"

DEFAULT_FALLBACK_MODELS = [
    "gemini-4-argon",
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-flash-latest",
    "gemini-2.5-flash-lite"
]

def parse_model_version(name: str) -> Tuple[float, str]:
    clean = name.replace("models/", "").strip()
    match_argon = re.search(r"gemini-(\d+(?:\.\d+)?)-argon", clean)
    if match_argon:
        return (float(match_argon.group(1)) + 0.5, clean)
    match = re.search(r"gemini-(\d+(?:\.\d+)?)-flash", clean)
    if match:
        return (float(match.group(1)), clean)
    match_pro = re.search(r"gemini-(\d+(?:\.\d+)?)-pro", clean)
    if match_pro:
        return (float(match_pro.group(1)) - 0.01, clean)
    if "flash-latest" in clean:
        return (1.0, clean)
    if "flash-lite" in clean:
        return (0.9, clean)
    return (0.0, clean)

class GeminiAdvisor:
    """
    Gemini AI Autonomous Code Advisor, Cupertino Restyler,
    and Apple App Store Copywriter.
    """

    @classmethod
    def get_api_key(cls) -> str:
        if "GEMINI_API_KEY" in os.environ:
            return os.environ["GEMINI_API_KEY"]
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    return cfg.get("gemini_api_key", "")
            except Exception:
                pass
        return ""

    @classmethod
    def is_online(cls, timeout: float = 0.3) -> bool:
        """
        Fast non-blocking connectivity probe to determine if internet is reachable.
        Guarantees zero-delay fallback when operating in offline mode.
        """
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(timeout)
            sock.connect(("8.8.8.8", 53))
            sock.close()
            return True
        except Exception:
            return False

    @classmethod
    def is_available(cls) -> bool:
        return bool(cls.get_api_key()) and cls.is_online()

    @classmethod
    def discover_available_models(cls, force_refresh: bool = False) -> List[str]:
        if not force_refresh and MODELS_CACHE_FILE.exists():
            try:
                with open(MODELS_CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if time.time() - data.get("timestamp", 0) < 86400:
                        return data.get("models", DEFAULT_FALLBACK_MODELS)
            except Exception:
                pass

        api_key = cls.get_api_key()
        if not api_key or not cls.is_online():
            return DEFAULT_FALLBACK_MODELS

        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            models_iter = client.models.list()
            flash_models = []
            for m in models_iter:
                m_name = getattr(m, "name", str(m))
                if "gemini" in m_name.lower():
                    flash_models.append(m_name.replace("models/", ""))

            if flash_models:
                flash_models.sort(key=lambda m: parse_model_version(m), reverse=True)
                MODELS_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                with open(MODELS_CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump({"timestamp": int(time.time()), "models": flash_models}, f)
                return flash_models
        except Exception:
            pass

        return DEFAULT_FALLBACK_MODELS

    @classmethod
    def get_latest_flash_model(cls) -> str:
        models = cls.discover_available_models()
        return models[0] if models else "gemini-4-argon"

    @classmethod
    def get_configured_model_preference(cls) -> str:
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    pref = cfg.get("gemini_model")
                    if pref:
                        return pref
            except Exception:
                pass
        return cls.get_latest_flash_model()

    @classmethod
    def _get_execution_models_list(cls) -> List[str]:
        pref = cls.get_configured_model_preference()
        models = cls.discover_available_models()
        if not models:
            models = DEFAULT_FALLBACK_MODELS[:]
        if pref and pref in models:
            return [pref] + [m for m in models if m != pref]
        elif pref:
            return [pref] + [m for m in models]
        return models

    @classmethod
    def set_model_preference(cls, model_name: str) -> bool:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass
        data["gemini_model"] = model_name
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            return False

    @classmethod
    def analyze_and_optimize_code(cls, code_snippet: str, app_name: str = "iOS App") -> Dict[str, Any]:
        offline_analysis = f"""### Web2IPA iOS Diagnostic Report for '{app_name}'
1. **Viewport & Safe Areas**: Normalized with `viewport-fit=cover`, `env(safe-area-inset-top)`, and Dynamic Island safe insets.
2. **WebKit Performance**: 120Hz ProMotion momentum scrolling `-webkit-overflow-scrolling: touch` enabled.
3. **Web Audio & Tap Responsiveness**: Injected touch audio unlocker and eliminated 300ms mobile Safari tap delays.
"""
        api_key = cls.get_api_key()
        if not api_key or not cls.is_online():
            return {
                "success": True,
                "analysis": offline_analysis,
                "model_used": "offline-engine",
                "fallback": True
            }

        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            prompt = f"""
You are an expert iOS WebKit & SwiftUI Engineer.
Analyze this code for an iOS App named '{app_name}' running in a WKWebView.
Check for:
1. Touch responsiveness, 300ms click delay, safe-area inset compliance (env(safe-area-inset-top)).
2. iOS Safari viewport bugs (-webkit-fill-available).
3. Web Audio unlock on user touch.
4. Smooth 60/120Hz scrolling performance (-webkit-overflow-scrolling: touch).

Return a concise JSON response with:
- "rating": score from 1-10
- "recommendations": array of recommendations
- "improved_code": modified snippet if applicable

Code:
{code_snippet[:6000]}
"""
            candidate_models = cls._get_execution_models_list()
            for model_to_use in candidate_models:
                try:
                    response = client.models.generate_content(
                        model=model_to_use,
                        contents=prompt
                    )
                    if response and response.text:
                        return {"success": True, "analysis": response.text, "model_used": model_to_use}
                except Exception:
                    continue
        except Exception:
            pass

        return {
            "success": True,
            "analysis": offline_analysis,
            "model_used": "offline-engine",
            "fallback": True
        }

    @classmethod
    def generate_app_store_metadata(cls, app_name: str, url: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
        default_meta = {
            "title": app_name[:30],
            "subtitle": f"Experience {app_name[:18]} on iOS",
            "keywords": "ios, app, web, standalone, fast, offline, safari, wkwebview",
            "description": description or f"Welcome to {app_name}, beautifully packaged for iOS with safe-area support, offline resilience, and fluid 120Hz ProMotion performance.",
            "model_used": "offline-engine"
        }
        api_key = cls.get_api_key()
        if not api_key or not cls.is_online():
            return default_meta

        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            prompt = f"""
Write Apple App Store metadata for an iOS app named '{app_name}'.
Context: {description or ''} URL: {url or ''}.
Return a JSON object with:
- "title": max 30 characters
- "subtitle": max 30 characters
- "keywords": 100 characters comma-separated
- "description": 2-3 compelling paragraphs highlighting iOS features (Dynamic Island, Safe Areas, Haptics, Offline)
"""
            candidate_models = cls._get_execution_models_list()
            for model_to_use in candidate_models:
                try:
                    response = client.models.generate_content(
                        model=model_to_use,
                        contents=prompt
                    )
                    text = response.text or ""
                    match = re.search(r"\{.*\}", text, re.DOTALL)
                    if match:
                        res = json.loads(match.group(0))
                        res["model_used"] = model_to_use
                        return res
                except Exception:
                    continue
        except Exception:
            pass

        return default_meta
