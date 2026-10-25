import os
import re
import shutil
from pathlib import Path
from typing import Dict, Any, List

class AssetOptimizer:
    """
    High-Performance Asset Minifier & Turbo Optimizer for iOS Web Assets.
    Strips development artifacts, source maps, and minifies HTML/CSS/JS
    to reduce bundle payload size and improve load times.
    """

    IGNORE_PATTERNS = [
        "*.map", ".git*", "node_modules", ".DS_Store", "Thumbs.db",
        "*.ts", "*.scss", "*.less", "package-lock.json", "yarn.lock"
    ]

    @classmethod
    def optimize_directory(cls, dir_path: Path) -> Dict[str, Any]:
        """
        Cleans and minifies all assets inside dir_path in-place.
        """
        initial_size = cls._get_dir_size(dir_path)
        files_cleaned = 0
        files_minified = 0

        # 1. Remove unwanted dev files and source maps
        for root, dirs, files in os.walk(dir_path, topdown=True):
            dirs[:] = [d for d in dirs if d not in ["node_modules", ".git", ".vscode", ".idea"]]
            for f in files:
                f_path = Path(root) / f
                if f.endswith(".map") or f in [".DS_Store", "Thumbs.db", "package-lock.json", "yarn.lock"]:
                    try:
                        f_path.unlink()
                        files_cleaned += 1
                    except Exception:
                        pass

        # 2. Minify CSS files
        for css_file in dir_path.glob("**/*.css"):
            try:
                content = css_file.read_text(encoding="utf-8", errors="ignore")
                minified = cls._minify_css(content)
                css_file.write_text(minified, encoding="utf-8")
                files_minified += 1
            except Exception:
                pass

        # 3. Minify HTML files
        for html_file in dir_path.glob("**/*.html"):
            try:
                content = html_file.read_text(encoding="utf-8", errors="ignore")
                minified = cls._minify_html(content)
                html_file.write_text(minified, encoding="utf-8")
                files_minified += 1
            except Exception:
                pass

        # 4. Clean JS comments
        for js_file in dir_path.glob("**/*.js"):
            if not js_file.name.endswith(".min.js"):
                try:
                    content = js_file.read_text(encoding="utf-8", errors="ignore")
                    minified = cls._minify_js(content)
                    js_file.write_text(minified, encoding="utf-8")
                    files_minified += 1
                except Exception:
                    pass

        final_size = cls._get_dir_size(dir_path)
        saved_bytes = max(0, initial_size - final_size)
        percent_saved = (saved_bytes / initial_size * 100) if initial_size > 0 else 0

        return {
            "initial_kb": round(initial_size / 1024, 2),
            "final_kb": round(final_size / 1024, 2),
            "saved_kb": round(saved_bytes / 1024, 2),
            "percent_saved": round(percent_saved, 1),
            "files_cleaned": files_cleaned,
            "files_minified": files_minified
        }

    @classmethod
    def _get_dir_size(cls, dir_path: Path) -> int:
        total = 0
        for root, _, files in os.walk(dir_path):
            for f in files:
                try:
                    total += (Path(root) / f).stat().st_size
                except Exception:
                    pass
        return total

    @staticmethod
    def _minify_css(css: str) -> str:
        css = re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL)
        css = re.sub(r'\s+', ' ', css)
        css = re.sub(r'\s*([\{\};:,])\s*', r'\1', css)
        css = re.sub(r';\}', '}', css)
        return css.strip()

    @staticmethod
    def _minify_html(html: str) -> str:
        html = re.sub(r'<!--(?!\s*\[if).*?-->', '', html, flags=re.DOTALL)
        html = re.sub(r'>\s+<', '><', html)
        return html.strip()

    @staticmethod
    def _minify_js(js: str) -> str:
        js = re.sub(r'/\*[\s\S]*?\*/', '', js)
        lines = [line.strip() for line in js.splitlines() if line.strip() and not line.strip().startswith('//')]
        return '\n'.join(lines)
