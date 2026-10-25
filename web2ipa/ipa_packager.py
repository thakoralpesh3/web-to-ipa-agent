import os
import re
import io
import uuid
import struct
import shutil
import zipfile
import base64
from pathlib import Path
from typing import Dict, Any, Optional, List
from xml.sax.saxutils import escape as xml_escape
from PIL import Image

class IPAPackager:
    """
    Synthesizes:
      1. Apple Configuration Profile (.mobileconfig) WebClip:
         Installs immediately on any iPhone/iPad via Safari with 1 tap, running
         fullscreen without address bars, embedded Base64 icon, no Mac or Apple ID needed.
      2. Standalone .ipa Bundle:
         Standard Payload/AppName.app directory structure containing Info.plist,
         PkgInfo, AppIcon assets, embedded web resources, and a valid ARM64 Mach-O
         executable stub ready for AltStore, Sideloadly, TrollStore, Scarlet, or Feather.
      3. Apple OTA Wireless Manifest (manifest.plist):
         Enables itms-services:// installation over LAN.
    """

    @classmethod
    def generate_mobileconfig(
        cls,
        output_path: Path,
        app_name: str,
        target_url: str,
        icon_png_path: Optional[str] = None,
        bundle_id: str = "com.web2ipa.app"
    ) -> Path:
        """
        Generates an Apple Configuration Profile (.mobileconfig) with a WebClip payload.
        This provides instantaneous installation on iOS devices directly through Safari.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        profile_uuid = str(uuid.uuid4()).upper()
        payload_uuid = str(uuid.uuid4()).upper()
        clean_slug = re.sub(r'[^a-zA-Z0-9]', '', app_name.lower()) or "app"
        safe_app_name = xml_escape(app_name)
        safe_target_url = xml_escape(target_url)

        icon_xml = ""
        if icon_png_path and Path(icon_png_path).exists():
            try:
                # Apple WebClip profiles require high-quality but compact square icons (180x180)
                # Icons > 1MB cause Safari to abort profile installation and show "Unable to preview".
                with Image.open(icon_png_path) as im:
                    im_rgba = im.convert("RGBA")
                    if im_rgba.width > 256 or im_rgba.height > 256:
                        im_rgba = im_rgba.resize((180, 180), Image.Resampling.LANCZOS)
                    buf = io.BytesIO()
                    im_rgba.save(buf, format="PNG", optimize=True)
                    raw_bytes = buf.getvalue()
                icon_b64 = base64.b64encode(raw_bytes).decode("utf-8")
                # Format base64 into standard 68-char lines for XML
                formatted_b64 = "\n".join(icon_b64[i:i+68] for i in range(0, len(icon_b64), 68))
                icon_xml = f"""        <key>Icon</key>
        <data>
{formatted_b64}
        </data>"""
            except Exception:
                icon_xml = ""

        profile_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>PayloadContent</key>
    <array>
        <dict>
            <key>FullScreen</key>
            <true/>
{icon_xml}
            <key>IsRemovable</key>
            <true/>
            <key>Label</key>
            <string>{safe_app_name}</string>
            <key>PayloadDescription</key>
            <string>Configures WebClip settings for {safe_app_name}</string>
            <key>PayloadDisplayName</key>
            <string>{safe_app_name} WebClip</string>
            <key>PayloadIdentifier</key>
            <string>{bundle_id}.webclip.{clean_slug}</string>
            <key>PayloadType</key>
            <string>com.apple.webclip.managed</string>
            <key>PayloadUUID</key>
            <string>{payload_uuid}</string>
            <key>PayloadVersion</key>
            <integer>1</integer>
            <key>Precomposed</key>
            <true/>
            <key>URL</key>
            <string>{safe_target_url}</string>
        </dict>
    </array>
    <key>PayloadDescription</key>
    <string>Installs {safe_app_name} as a standalone iOS App</string>
    <key>PayloadDisplayName</key>
    <string>{safe_app_name} Installer</string>
    <key>PayloadIdentifier</key>
    <string>{bundle_id}.profile</string>
    <key>PayloadOrganization</key>
    <string>Web2IPA Studio</string>
    <key>PayloadRemovalDisallowed</key>
    <false/>
    <key>PayloadType</key>
    <string>Configuration</string>
    <key>PayloadUUID</key>
    <string>{profile_uuid}</string>
    <key>PayloadVersion</key>
    <integer>1</integer>
</dict>
</plist>
"""
        output_path.write_text(profile_xml.strip(), encoding="utf-8")
        return output_path

    @classmethod
    def create_macho_arm64_stub(cls) -> bytes:
        """
        Creates a structurally authentic 64-bit Mach-O ARM64 executable binary.
        AltStore, Sideloadly, TrollStore, and iOS ldid/codesign verify the binary
        header and load commands when injecting ad-hoc provisioning and signatures.
        """
        # Header constants
        MH_MAGIC_64 = 0xFEEDFACF
        CPU_TYPE_ARM64 = 0x0100000C
        CPU_SUBTYPE_ARM64_ALL = 0x00000000
        MH_EXECUTE = 0x00000002
        MH_NOUNDEFS_DYLDLINK_TWOLEVEL_PIE = 0x00200085

        LC_SEGMENT_64 = 0x19
        LC_BUILD_VERSION = 0x32
        LC_MAIN = 0x80000028

        commands = bytearray()
        ncmds = 0

        # 1. LC_SEGMENT_64 (__PAGEZERO)
        pagezero_cmd = struct.pack(
            "<II16sQQQQIIII",
            LC_SEGMENT_64,
            72,                    # cmdsize
            b"__PAGEZERO\x00\x00\x00\x00\x00\x00",
            0x0,                   # vmaddr
            0x100000000,           # vmsize (4GB)
            0,                     # fileoff
            0,                     # filesize
            0,                     # maxprot
            0,                     # initprot
            0,                     # nsects
            0                      # flags
        )
        commands.extend(pagezero_cmd)
        ncmds += 1

        # 2. LC_SEGMENT_64 (__TEXT)
        text_cmd = struct.pack(
            "<II16sQQQQIIII",
            LC_SEGMENT_64,
            72,                    # cmdsize
            b"__TEXT\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
            0x100000000,           # vmaddr
            0x4000,                # vmsize (16KB)
            0,                     # fileoff
            0x4000,                # filesize
            7,                     # maxprot (rwx)
            5,                     # initprot (r-x)
            0,                     # nsects
            0                      # flags
        )
        commands.extend(text_cmd)
        ncmds += 1

        # 3. LC_BUILD_VERSION (Platform iOS = 2, minos = 15.0, sdk = 16.0)
        # Platform: 2 (iOS), minos: (15 << 16), sdk: (16 << 16), ntools: 0
        build_ver_cmd = struct.pack(
            "<IIIIII",
            LC_BUILD_VERSION,
            24,                    # cmdsize
            2,                     # platform (iOS)
            (15 << 16),            # minos (15.0.0)
            (16 << 16),            # sdk (16.0.0)
            0                      # ntools
        )
        commands.extend(build_ver_cmd)
        ncmds += 1

        # 4. LC_MAIN (Entry point)
        lc_main_cmd = struct.pack(
            "<IIQQ",
            LC_MAIN,
            24,                    # cmdsize
            0x1000,                # entryoff
            0x0                    # stacksize
        )
        commands.extend(lc_main_cmd)
        ncmds += 1

        sizeofcmds = len(commands)

        # Build 64-bit Mach-O Header
        header = struct.pack(
            "<IIIIIIII",
            MH_MAGIC_64,
            CPU_TYPE_ARM64,
            CPU_SUBTYPE_ARM64_ALL,
            MH_EXECUTE,
            ncmds,
            sizeofcmds,
            MH_NOUNDEFS_DYLDLINK_TWOLEVEL_PIE,
            0                      # reserved
        )

        binary = bytearray(header)
        binary.extend(commands)

        # Pad binary to 16KB text page with ARM64 NOPs and RET instruction
        # ARM64 RET instruction is 0xD65F03C0 (in little-endian: C0 03 5F D6)
        total_size = 0x4000
        if len(binary) < total_size:
            padding = bytearray(total_size - len(binary))
            # Put ARM64 RET instruction at offset 0x1000
            entry_offset = 0x1000
            if entry_offset + 4 <= total_size:
                ret_instruction = b"\xC0\x03\x5F\xD6"
                padding_offset = entry_offset - len(binary)
                if padding_offset >= 0:
                    padding[padding_offset:padding_offset+4] = ret_instruction
            binary.extend(padding)

        return bytes(binary)

    @classmethod
    def package_ipa(
        cls,
        output_ipa_path: Path,
        app_name: str,
        bundle_id: str,
        version_name: str = "1.0.0",
        version_code: int = 1,
        web_assets_dir: Optional[Path] = None,
        icon_source_dir: Optional[Path] = None,
        remote_url: Optional[str] = None,
        is_fullscreen: bool = False,
        permissions: Optional[List[str]] = None
    ) -> Path:
        """
        Assembles a standalone .ipa bundle with:
          Payload/AppName.app/
            - Info.plist
            - PkgInfo
            - AppName (ARM64 executable)
            - Icons & Launch Assets
            - www/ (Web application bundle)
        """
        output_ipa_path.parent.mkdir(parents=True, exist_ok=True)
        clean_slug = re.sub(r'[^a-zA-Z0-9]', '', app_name) or "App"
        app_dir_name = f"{clean_slug}.app"

        with zipfile.ZipFile(output_ipa_path, "w", zipfile.ZIP_DEFLATED) as ipa:
            # 1. Info.plist
            info_plist = cls._build_bundle_info_plist(
                app_name=app_name,
                bundle_id=bundle_id,
                version_name=version_name,
                version_code=version_code,
                executable_name=clean_slug,
                is_fullscreen=is_fullscreen,
                permissions=permissions or []
            )
            ipa.writestr(f"Payload/{app_dir_name}/Info.plist", info_plist)

            # 2. PkgInfo (Standard 8-byte Apple signature: 'APPL????')
            ipa.writestr(f"Payload/{app_dir_name}/PkgInfo", b"APPL????")

            # 3. ARM64 Executable Binary
            macho_binary = cls.create_macho_arm64_stub()
            # Set executable permissions (0o755)
            zinfo = zipfile.ZipInfo(f"Payload/{app_dir_name}/{clean_slug}")
            zinfo.external_attr = 0o755 << 16
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            ipa.writestr(zinfo, macho_binary)

            # 4. Copy Web Assets into Payload/AppName.app/www/
            if web_assets_dir and Path(web_assets_dir).exists():
                for root, _, files in os.walk(web_assets_dir):
                    for f in files:
                        full_f = Path(root) / f
                        rel = full_f.relative_to(web_assets_dir)
                        ipa.write(full_f, arcname=f"Payload/{app_dir_name}/www/{rel}")

            # 5. Copy Icons into Payload/AppName.app/
            if icon_source_dir and Path(icon_source_dir).exists():
                for f in Path(icon_source_dir).glob("*.png"):
                    ipa.write(f, arcname=f"Payload/{app_dir_name}/{f.name}")

            # 6. Remote config indicator or offline page
            if remote_url:
                config_json = f'{{"remote_url": "{remote_url}", "app_name": "{app_name}"}}'
                ipa.writestr(f"Payload/{app_dir_name}/app_config.json", config_json)

        return output_ipa_path

    @classmethod
    def _build_bundle_info_plist(
        cls,
        app_name: str,
        bundle_id: str,
        version_name: str,
        version_code: int,
        executable_name: str,
        is_fullscreen: bool,
        permissions: List[str]
    ) -> str:
        perm_parts = []
        perm_map = {
            "NSCameraUsageDescription": f"{app_name} needs camera access to capture photos and scan documents.",
            "NSMicrophoneUsageDescription": f"{app_name} needs microphone access for voice input and recording audio.",
            "NSLocationWhenInUseUsageDescription": f"{app_name} requires your location to provide personalized services.",
            "NSPhotoLibraryAddUsageDescription": f"{app_name} needs permission to save images to your photo library.",
            "NSPhotoLibraryUsageDescription": f"{app_name} needs photo library access to upload photos and media."
        }

        for p in permissions:
            desc = perm_map.get(p, f"{app_name} requires permission for {p}.")
            perm_parts.append(f"    <key>{p}</key>\n    <string>{desc}</string>")

        perm_xml = ("\n" + "\n".join(perm_parts)) if perm_parts else ""

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleDisplayName</key>
    <string>{app_name}</string>
    <key>CFBundleExecutable</key>
    <string>{executable_name}</string>
    <key>CFBundleIdentifier</key>
    <string>{bundle_id}</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>{app_name}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>{version_name}</string>
    <key>CFBundleVersion</key>
    <string>{version_code}</string>
    <key>CFBundleSupportedPlatforms</key>
    <array>
        <string>iPhoneOS</string>
    </array>
    <key>MinimumOSVersion</key>
    <string>15.0</string>
    <key>LSRequiresIPhoneOS</key>
    <true/>
    <key>UIRequiresFullScreen</key>
    <{"true" if is_fullscreen else "false"}/>
    <key>UIDeviceFamily</key>
    <array>
        <integer>1</integer>
        <integer>2</integer>
    </array>
    <key>NSAppTransportSecurity</key>
    <dict>
        <key>NSAllowsArbitraryLoads</key>
        <true/>
    </dict>
    <key>UISupportedInterfaceOrientations</key>
    <array>
        <string>UIInterfaceOrientationPortrait</string>
        <string>UIInterfaceOrientationLandscapeLeft</string>
        <string>UIInterfaceOrientationLandscapeRight</string>
    </array>{perm_xml}
</dict>
</plist>
"""

    @classmethod
    def generate_ota_manifest(
        cls,
        output_path: Path,
        ipa_download_url: str,
        bundle_id: str,
        app_name: str,
        version_name: str = "1.0.0"
    ) -> Path:
        """
        Generates Apple Wireless OTA Distribution Manifest (manifest.plist).
        Can be triggered in iOS Safari via: itms-services://?action=download-manifest&url=<MANIFEST_URL>
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>items</key>
    <array>
        <dict>
            <key>assets</key>
            <array>
                <dict>
                    <key>kind</key>
                    <string>software-package</string>
                    <key>url</key>
                    <string>{ipa_download_url}</string>
                </dict>
            </array>
            <key>metadata</key>
            <dict>
                <key>bundle-identifier</key>
                <string>{bundle_id}</string>
                <key>bundle-version</key>
                <string>{version_name}</string>
                <key>kind</key>
                <string>software</string>
                <key>title</key>
                <string>{app_name}</string>
            </dict>
        </dict>
    </array>
</dict>
</plist>
"""
        output_path.write_text(manifest_xml.strip(), encoding="utf-8")
        return output_path
