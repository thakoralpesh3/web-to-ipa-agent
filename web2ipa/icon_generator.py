"""
Apple AppIcon Catalog & Asset Generator
Converts vector SVGs, PNGs, JPGs, ICOs, or generated badges into the complete
Apple iOS AppIcon.appiconset catalog with Contents.json, supporting 1x/2x/3x and 1024x1024.
"""

import os
import re
import io
import json
import base64
import urllib.parse
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from PIL import Image, ImageDraw, ImageFont
import requests

try:
    import cairosvg
    HAS_CAIROSVG = True
except (ImportError, OSError):
    HAS_CAIROSVG = False


class iOSIconGenerator:
    """
    Generates all iOS App Icon resolutions, Asset Catalogs, and WebClip icons.
    """

    # Exact Apple iOS AppIcon specifications
    IOS_ICON_SPECS = [
        {"idiom": "iphone", "size": "20x20", "scale": "2x", "pixels": 40, "filename": "AppIcon-20@2x.png"},
        {"idiom": "iphone", "size": "20x20", "scale": "3x", "pixels": 60, "filename": "AppIcon-20@3x.png"},
        {"idiom": "iphone", "size": "29x29", "scale": "2x", "pixels": 58, "filename": "AppIcon-29@2x.png"},
        {"idiom": "iphone", "size": "29x29", "scale": "3x", "pixels": 87, "filename": "AppIcon-29@3x.png"},
        {"idiom": "iphone", "size": "40x40", "scale": "2x", "pixels": 80, "filename": "AppIcon-40@2x.png"},
        {"idiom": "iphone", "size": "40x40", "scale": "3x", "pixels": 120, "filename": "AppIcon-40@3x.png"},
        {"idiom": "iphone", "size": "60x60", "scale": "2x", "pixels": 120, "filename": "AppIcon-60@2x.png"},
        {"idiom": "iphone", "size": "60x60", "scale": "3x", "pixels": 180, "filename": "AppIcon-60@3x.png"},
        {"idiom": "ipad", "size": "20x20", "scale": "1x", "pixels": 20, "filename": "AppIcon-20~ipad.png"},
        {"idiom": "ipad", "size": "20x20", "scale": "2x", "pixels": 40, "filename": "AppIcon-20@2x~ipad.png"},
        {"idiom": "ipad", "size": "29x29", "scale": "1x", "pixels": 29, "filename": "AppIcon-29~ipad.png"},
        {"idiom": "ipad", "size": "29x29", "scale": "2x", "pixels": 58, "filename": "AppIcon-29@2x~ipad.png"},
        {"idiom": "ipad", "size": "40x40", "scale": "1x", "pixels": 40, "filename": "AppIcon-40~ipad.png"},
        {"idiom": "ipad", "size": "40x40", "scale": "2x", "pixels": 80, "filename": "AppIcon-40@2x~ipad.png"},
        {"idiom": "ipad", "size": "76x76", "scale": "1x", "pixels": 76, "filename": "AppIcon-76~ipad.png"},
        {"idiom": "ipad", "size": "76x76", "scale": "2x", "pixels": 152, "filename": "AppIcon-76@2x~ipad.png"},
        {"idiom": "ipad", "size": "83.5x83.5", "scale": "2x", "pixels": 167, "filename": "AppIcon-83.5@2x~ipad.png"},
        {"idiom": "ios-marketing", "size": "1024x1024", "scale": "1x", "pixels": 1024, "filename": "AppIcon-1024.png"}
    ]

    @classmethod
    def load_master_image(cls, source: Optional[str], app_name: str = "Web App") -> Image.Image:
        """Loads and normalizes an icon from local path, remote URL, SVG, or generates a badge."""
        if not source:
            return cls.generate_default_badge(app_name, 1024)

        source_str = str(source).strip()

        # 1. Remote URL
        if source_str.startswith(("http://", "https://")):
            try:
                headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)"}
                resp = requests.get(source_str, headers=headers, timeout=10)
                if resp.status_code == 200:
                    content_type = resp.headers.get("Content-Type", "").lower()
                    if "svg" in content_type or source_str.lower().endswith(".svg"):
                        img = cls.rasterize_svg_content(resp.text, 1024)
                        if img:
                            return img
                    return Image.open(io.BytesIO(resp.content)).convert("RGBA").resize((1024, 1024), Image.Resampling.LANCZOS)
            except Exception:
                pass
            return cls.generate_default_badge(app_name, 1024)

        # 2. Local File
        src_path = Path(source_str)
        if src_path.exists() and src_path.is_file():
            if src_path.suffix.lower() == ".svg":
                img = cls.rasterize_svg_file(src_path, 1024)
                if img:
                    return img
            try:
                raw_img = Image.open(src_path).convert("RGBA")
                return raw_img.resize((1024, 1024), Image.Resampling.LANCZOS)
            except Exception:
                pass

        return cls.generate_default_badge(app_name, 1024)

    @classmethod
    def generate_appiconset(cls, source: Optional[str], target_appiconset_dir: Path, app_name: str = "Web App") -> Path:
        """
        Generates the full Apple AppIcon.appiconset directory containing
        all required PNG assets and the standard Contents.json manifest.
        """
        target_dir = Path(target_appiconset_dir).resolve()
        target_dir.mkdir(parents=True, exist_ok=True)

        master_img = cls.load_master_image(source, app_name)

        images_json_list = []
        created_files = set()

        for spec in cls.IOS_ICON_SPECS:
            filename = spec["filename"]
            px = spec["pixels"]
            out_file = target_dir / filename

            if filename not in created_files:
                resized = master_img.resize((px, px), Image.Resampling.LANCZOS)
                # iOS App Store guidelines require no alpha transparency on the 1024x1024 icon
                if px == 1024:
                    bg = Image.new("RGBA", (px, px), (15, 23, 42, 255))
                    bg.paste(resized, (0, 0), resized)
                    bg.convert("RGB").save(out_file, format="PNG")
                else:
                    resized.save(out_file, format="PNG")
                created_files.add(filename)

            images_json_list.append({
                "idiom": spec["idiom"],
                "size": spec["size"],
                "scale": spec["scale"],
                "filename": filename
            })

        contents_json = {
            "images": images_json_list,
            "info": {
                "author": "xcode",
                "version": 1
            }
        }

        with open(target_dir / "Contents.json", "w", encoding="utf-8") as f:
            json.dump(contents_json, f, indent=2)

        return target_dir

    @classmethod
    def generate_apple_icon_catalog(cls, output_dir: Path, source_icon_path: Optional[str] = None, app_name: str = "iOS App", theme_color: str = "#000000") -> Dict[str, Any]:
        p = cls.generate_appiconset(source_icon_path, output_dir, app_name)
        return {"success": True, "path": str(p)}

    @classmethod
    def cache_normalized_icon(cls, source: str, app_name: str) -> Tuple[Optional[Path], Optional[str]]:
        """Saves a 512x512 PNG copy in ~/.web2ipa/icons and returns (Path, base64_data_uri)."""
        try:
            cache_dir = Path.home() / ".web2ipa" / "icons"
            cache_dir.mkdir(parents=True, exist_ok=True)

            slug = re.sub(r"[^a-zA-Z0-9]", "_", app_name).lower()[:25]
            out_path = cache_dir / f"icon_{slug}.png"

            img = cls.load_master_image(source, app_name)
            thumb = img.resize((512, 512), Image.Resampling.LANCZOS)
            thumb.save(out_path, format="PNG")

            buffered = io.BytesIO()
            thumb.save(buffered, format="PNG")
            b64_str = f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"

            return out_path, b64_str
        except Exception:
            return None, None

    @classmethod
    def rasterize_svg_file(cls, svg_path: Path, size: int = 1024) -> Optional[Image.Image]:
        """Rasterizes SVG file via CairoSVG with anti-aliasing."""
        if not HAS_CAIROSVG:
            return None
        try:
            png_bytes = cairosvg.svg2png(url=str(svg_path.resolve()), output_width=size, output_height=size)
            if png_bytes:
                return Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        except Exception:
            pass
        return None

    @classmethod
    def rasterize_svg_content(cls, svg_str: str, size: int = 1024) -> Optional[Image.Image]:
        """Rasterizes inline SVG string via CairoSVG."""
        if not HAS_CAIROSVG:
            return None
        try:
            png_bytes = cairosvg.svg2png(bytestring=svg_str.encode("utf-8"), output_width=size, output_height=size)
            if png_bytes:
                return Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        except Exception:
            pass
        return None

    @classmethod
    def generate_default_badge(cls, app_name: str, size: int = 1024) -> Image.Image:
        """
        Generates a premium Apple Cupertino squircle badge with gradient and monograms.
        """
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Gradient background
        for y in range(size):
            ratio = y / size
            r = int(14 + (2 - 14) * ratio)
            g = int(165 + (132 - 165) * ratio)
            b = int(233 + (241 - 233) * ratio)
            draw.line([(0, y), (size, y)], fill=(r, g, b, 255))

        # Apple rounded squircle mask
        corner_rad = int(size * 0.22)
        mask = Image.new("L", (size, size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([(0, 0), (size, size)], radius=corner_rad, fill=255)

        # Apply mask
        output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        output.paste(img, (0, 0), mask)

        # Draw Letter Monogram
        clean = re.sub(r"[^a-zA-Z0-9]", "", app_name).upper()
        initials = clean[:2] if len(clean) >= 2 else (clean[:1] or "IO")

        draw_out = ImageDraw.Draw(output)
        font_size = int(size * 0.42)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

        # Center text
        bbox = draw_out.textbbox((0, 0), initials, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = (size - w) / 2
        y = (size - h) / 2 - (bbox[1] if bbox[1] < 0 else 0)

        # Drop shadow & text
        draw_out.text((x, y + 6), initials, fill=(0, 0, 0, 60), font=font)
        draw_out.text((x, y), initials, fill=(255, 255, 255, 255), font=font)

        return output
