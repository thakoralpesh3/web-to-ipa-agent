import os
import re
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

MEMORY_FILE = Path.home() / ".web2ipa" / "memory.json"
INNOVATIONS_FILE = Path.home() / ".web2ipa" / "innovations.json"

class EvolutionEngine:
    """
    Self-Learning & Evolutionary Growth Engine for Web2IPA.
    Tracks project structures, frameworks, self-healing repairs, XP/rank,
    and synthesizes autonomous innovations.
    """

    FRAMEWORK_SIGNATURES = {
        "Phaser 3 Game Engine": [r"phaser\.min\.js", r"phaser\.js", r"Phaser\.Game"],
        "Three.js / WebGL 3D": [r"three\.min\.js", r"three\.js", r"THREE\.Scene", r"three/build"],
        "Godot Engine HTML5": [r"godot\.js", r"engine\.js", r"\$Godot"],
        "Construct 3 / 2": [r"c3runtime\.js", r"c2runtime\.js"],
        "Unity WebGL": [r"UnityLoader\.js", r"unityInstance", r"Build/.*\.framework\.js"],
        "React SPA": [r"react\.production\.min\.js", r"react-dom", r"_react", r"__REACT_DEVTOOLS_GLOBAL_HOOK__"],
        "Vue.js App": [r"vue\.min\.js", r"vue\.runtime", r"__VUE__", r"v-app"],
        "Vite Modern Bundle": [r"@vite", r"/assets/index-.*\.js", r"vite/client"],
        "Next.js Static Export": [r"_next/static", r"__NEXT_DATA__"],
        "Svelte Framework": [r"svelte", r"__svelte"],
        "PixiJS 2D Engine": [r"pixi\.min\.js", r"PIXI\.Application"],
        "Tailwind CSS App": [r"tailwindcss", r"tailwind\.css"],
        "Vanilla HTML5 / Modern JS": []
    }

    @classmethod
    def identify_framework(cls, dir_path: Path) -> str:
        all_text = ""
        files = list(dir_path.glob("**/*.html")) + list(dir_path.glob("**/*.js")) + list(dir_path.glob("package.json"))
        
        for f in files[:15]:
            try:
                all_text += f.read_text(encoding="utf-8", errors="ignore") + "\n"
            except Exception:
                pass

        for framework, signatures in cls.FRAMEWORK_SIGNATURES.items():
            for sig in signatures:
                if re.search(sig, all_text):
                    return framework

        return "Vanilla HTML5 / Modern JS"

    @classmethod
    def load_memory(cls) -> Dict[str, Any]:
        if MEMORY_FILE.exists():
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        default_memory = {
            "version": "1.0.0",
            "xp": 150,
            "level": 1,
            "rank": "Apprentice iOS AI Builder",
            "total_builds": 0,
            "successful_builds": 0,
            "total_repairs_applied": 0,
            "innovations_invented": 0,
            "frameworks_mastered": {},
            "learned_solutions": [
                "Auto-promotes nested build folders (dist, build, out) to root index.html",
                "Injects viewport-fit=cover & env(safe-area-inset-top/bottom) for iPhone notch & Dynamic Island",
                "Fixes iOS Safari 100vh jumping scroll bar bug via -webkit-fill-available",
                "Unlocks suspended Web Audio contexts on first touch gesture",
                "Disables 300ms double-tap delay for instantaneous touch response",
                "Detects Camera, Mic, and Location APIs and injects Apple Privacy Usage Descriptions",
                "Synthesizes Apple Asset Catalogs across all 18 resolutions + 1024x1024 App Store icon",
                "Builds valid 64-bit ARM64 Mach-O executables for AltStore, Sideloadly & TrollStore",
                "Generates 1-tap .mobileconfig WebClip profiles with embedded Base64 icons"
            ],
            "build_history": []
        }
        cls.save_memory(default_memory)
        return default_memory

    @classmethod
    def save_memory(cls, data: Dict[str, Any]):
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load_innovations(cls) -> List[Dict[str, Any]]:
        if INNOVATIONS_FILE.exists():
            try:
                with open(INNOVATIONS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    @classmethod
    def record_innovation(cls, innovation: Dict[str, Any]):
        innovations = cls.load_innovations()
        innovation["timestamp"] = int(time.time())
        innovations = [innovation] + innovations[:50]
        INNOVATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(INNOVATIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(innovations, f, indent=2)

    @classmethod
    def calculate_rank(cls, xp: int) -> Tuple[int, str]:
        level = min(10, 1 + xp // 300)
        ranks = {
            1: "Apprentice iOS AI Builder",
            2: "Junior Swift Systems Engineer",
            3: "Adaptive WKWebView Specialist",
            4: "Cupertino UI/UX Craftsman",
            5: "Multi-Platform Apple Architect",
            6: "Autonomous Dynamic Island Master",
            7: "Advanced Mach-O Toolchain Engineer",
            8: "High-Performance iOS Compiler AI",
            9: "Evolutionary Apple Grandmaster",
            10: "Transcendent Universal Singularity"
        }
        return level, ranks.get(level, "Universal iOS Agent")

    @classmethod
    def record_build(
        cls,
        app_name: str,
        framework: str,
        success: bool,
        repairs: List[str],
        permissions: List[str],
        ipa_size_mb: float = 0.0
    ) -> Dict[str, Any]:
        mem = cls.load_memory()
        mem["total_builds"] += 1
        if success:
            mem["successful_builds"] += 1
            xp_gained = 50 + (len(repairs) * 25)
            mem["xp"] += xp_gained
        else:
            mem["xp"] += 10

        f_count = mem["frameworks_mastered"].get(framework, 0)
        mem["frameworks_mastered"][framework] = f_count + 1
        mem["total_repairs_applied"] += len(repairs)

        lvl, rank = cls.calculate_rank(mem["xp"])
        mem["level"] = lvl
        mem["rank"] = rank

        build_entry = {
            "app_name": app_name,
            "framework": framework,
            "success": success,
            "repairs_count": len(repairs),
            "permissions_count": len(permissions),
            "ipa_size_mb": ipa_size_mb,
            "timestamp": int(time.time())
        }
        mem["build_history"] = [build_entry] + mem["build_history"][:30]
        cls.save_memory(mem)

        return {
            "xp": mem["xp"],
            "level": lvl,
            "rank": rank,
            "total_builds": mem["total_builds"],
            "successful_builds": mem["successful_builds"]
        }

    @classmethod
    def generate_surprise_innovations(cls, app_name: str, html_snippet: str = "", framework: str = "") -> Dict[str, Any]:
        """Generates dynamic innovation suggestions for the app."""
        ideas = [
            {
                "title": "Haptic Feedback Engine",
                "description": "Trigger native Taptic Engine pulses on iOS when buttons or cards are tapped via window.webkit.messageHandlers.iOSApp.",
                "type": "HAPTICS"
            },
            {
                "title": "Dynamic Island & Notch CSS Safe-Area Adaptation",
                "description": "Seamlessly inset the navigation header using env(safe-area-inset-top) so content floats smoothly around the camera island.",
                "type": "DYNAMIC_ISLAND"
            },
            {
                "title": "Native iOS Share Sheet Polyfill",
                "description": "Route navigator.share() directly to UIActivityViewController to enable native AirDrop, Messages, and WhatsApp sharing.",
                "type": "SHARE_SHEET"
            },
            {
                "title": "Instant Safari WebClip (.mobileconfig)",
                "description": "1-tap direct install profile that creates a full-screen app icon on the iPhone Home Screen without any Mac or signing account.",
                "type": "WEBCLIP"
            }
        ]
        return {
            "success": True,
            "app_name": app_name,
            "framework": framework,
            "innovations": ideas
        }
