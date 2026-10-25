#!/usr/bin/env python3
"""
Web2IPA AI Agent & Studio
Autonomous tool for transforming Web applications and URLs into native iOS Apps (.ipa),
Swift / WKWebView Xcode Projects (.xcodeproj.zip), and 1-Tap Safari Profiles (.mobileconfig).
Includes iOS Self-Healing, Dynamic Island Insets, Apple Asset Catalog, and Wi-Fi QR Sideloading.
"""

import sys
import os
import argparse
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

from web2ipa.builder import IPABuilder, OUTPUT_DIR
from web2ipa.qr_server import QRServer, start_server_in_background
from web2ipa.watcher import start_dropzone_watcher, DROPZONE_DIR
from web2ipa.gui.server import start_server
from web2ipa.self_healer import iOSSelfHealer
from web2ipa.evolution import EvolutionEngine
from web2ipa.app_inspector import iOSAppInspector
from web2ipa.ai_advisor import GeminiAdvisor

console = Console()

def print_banner():
    mode_status = "[green]● Online[/green]" if GeminiAdvisor.is_online() else "[yellow]📴 Offline Mode (Local Zero-Network Engine)[/yellow]"
    banner_text = f"""[bold cyan]╦ ╦┌─┐┌┐ ┌─┐╦╔═╗╔═╗  ╔═╗╦  ╔═╗┌─┐┌─┐┌┐┌┌┬┐[/bold cyan]
[bold cyan]║║║├┤ ├┴┐┌─┘║╠═╝╠═╣  ╠═╣║  ╠═╣│ ┬├┤ │││ │ [/bold cyan]
[bold cyan]╚╩╝└─┘└─┘└─┘╩╩  ╩ ╩  ╩ ╩╩  ╩ ╩└─┘└─┘┘└┘ ┴ [/bold cyan]
[dim]Universal iOS App Studio • Standalone IPA • 1-Tap WebClip • Swift Xcode Project[/dim]
Status: {mode_status}"""
    console.print(Panel(banner_text, border_style="blue", expand=False))

def show_growth_memory():
    print_banner()
    console.print("\n[bold magenta]🧠 Web2IPA AI Evolution & Knowledge Memory[/bold magenta]\n")
    mem = EvolutionEngine.load_memory()

    table = Table(title="Agent Neural Metrics", border_style="blue")
    table.add_column("Metric", style="bold white")
    table.add_column("Value", style="bold cyan")
    table.add_column("Status / Level", style="green")

    table.add_row("Agent Evolution Level", f"Level {mem['level']}", f"[bold yellow]{mem['rank']}[/bold yellow]")
    table.add_row("Accumulated Experience", f"{mem['xp']} XP", "Growing continuously")
    table.add_row("Total iOS Builds", str(mem["total_builds"]), f"{mem['successful_builds']} Successful")
    table.add_row("Autonomous Self-Repairs", str(mem["total_repairs_applied"]), "Defects Auto-Resolved")

    console.print(table)

    if mem.get("frameworks_mastered"):
        f_table = Table(title="Frameworks Cataloged & Mastered", border_style="cyan")
        f_table.add_column("Framework / Engine", style="bold white")
        f_table.add_column("Projects Mastered", style="bold green")
        for fw, count in mem["frameworks_mastered"].items():
            f_table.add_row(fw, f"{count} projects")
        console.print(f_table)

    console.print("\n[bold cyan]💡 Learned Auto-Repair Recipes & iOS Polyfills:[/bold cyan]")
    for sol in mem.get("learned_solutions", []):
        console.print(f"  [green]✓[/green] {sol}")

def run_self_heal(path_str: str):
    print_banner()
    target_path = Path(path_str)
    if not target_path.exists():
        console.print(f"[bold red]❌ Error: Path '{path_str}' does not exist![/bold red]")
        return

    console.print(f"\n[bold cyan]🛡️ Running Autonomous iOS Self-Healer on:[/bold cyan] {target_path}\n")
    res = iOSSelfHealer.diagnose_and_heal_directory(target_path)
    
    table = Table(title="Diagnostic & Auto-Repair Summary", border_style="green")
    table.add_column("Category", style="bold white")
    table.add_column("Details", style="dim")

    table.add_row("Issues Discovered", ", ".join(res["issues_detected"]) if res["issues_detected"] else "None (Clean)")
    table.add_row("Repairs Applied", "\n".join([f"✓ {r}" for r in res["repairs_made"]]) if res["repairs_made"] else "No repairs required")
    table.add_row("Detected iOS Permissions", ", ".join(res["detected_permissions"]) if res["detected_permissions"] else "None")

    console.print(table)
    console.print("\n[bold green]🎉 Project healed and optimized for iOS WKWebView![/bold green]")

def run_inspect(target: str):
    print_banner()
    console.print(f"\n[bold cyan]🔍 Deeply Inspecting iOS Target:[/bold cyan] {target}\n")
    bp = iOSAppInspector.inspect(target)

    table = Table(title="iOS Blueprint Extraction", border_style="blue")
    table.add_column("Property", style="bold white")
    table.add_column("Detected Value", style="bold cyan")

    table.add_row("Application Title", bp.get("app_name", "Unknown"))
    table.add_row("Bundle Identifier", bp.get("bundle_id", "com.web2ipa.app"))
    table.add_row("Theme Color", bp.get("theme_color", "#000000"))
    table.add_row("Screen Orientation", bp.get("orientation", "universal"))
    table.add_row("Icon Asset Found", str(bp.get("icon_path", "Auto-generated monogram")))
    perms = list(bp.get("ios_permissions", {}).keys())
    table.add_row("iOS Privacy Permissions", ", ".join(perms) if perms else "None required")

    console.print(table)

def display_success_and_serve(res: dict, default_port: int = 8992, wait_for_user: bool = True):
    ipa_name = res["ipa_name"]
    mobileconfig_name = res["mobileconfig_name"]
    zip_name = res["xcodeproj_zip_name"]
    ipa_size_mb = res["ipa_size_mb"]

    table = Table(title="🍎 Build Deliverables Ready", border_style="green")
    table.add_column("Artifact", style="bold white")
    table.add_column("Type / Target", style="bold cyan")
    table.add_column("Filename", style="dim")

    table.add_row("1-Tap Safari Profile", "Instant iPhone Install (.mobileconfig)", mobileconfig_name)
    table.add_row("Standalone IPA", f"AltStore / Sideloadly Bundle ({ipa_size_mb:.2f} MB)", ipa_name)
    table.add_row("Xcode Project", "Native Swift / WKWebView Source", zip_name)
    console.print(table)

    # Launch background QR Wi-Fi Sideload server
    start_server_in_background(port=default_port)
    dl_url = QRServer.get_download_url(ipa_name, port=default_port)

    local_ip = QRServer.get_local_ip()
    base_url = f"http://{local_ip}:{default_port}"
    dl_table = Table(title="📥 Direct Download & Install Links", border_style="blue")
    dl_table.add_column("Deliverable", style="bold white")
    dl_table.add_column("Direct URL", style="underline cyan")
    dl_table.add_row("⚡ 1-Tap Safari Profile", f"{base_url}/install-profile/{mobileconfig_name}")
    dl_table.add_row("📦 Standalone Sideload IPA", f"{base_url}/download-raw/{ipa_name}")
    dl_table.add_row("🛠️ Swift Xcode Project", f"{base_url}/download-raw/{zip_name}")
    console.print(dl_table)

    console.print(f"\n[bold green]⚡ Wi-Fi Sideload Landing Page:[/bold green] [underline cyan]{dl_url}[/underline cyan]")
    console.print("[dim]Scan this QR code with your iPhone / iPad Camera to install directly over Wi-Fi:[/dim]\n")
    QRServer.generate_terminal_qr(dl_url)

    if wait_for_user:
        try:
            console.print("\n[bold yellow]📡 Server running. Press Ctrl+C to stop.[/bold yellow]")
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            console.print("\n[dim]Wi-Fi Server stopped.[/dim]")

def run_interactive_wizard():
    print_banner()
    console.print("\n[bold cyan]🧙‍♂️ Welcome to the Web2IPA Interactive Wizard![/bold cyan]\n")

    source_type = Prompt.ask("Choose source type", choices=["url", "folder", "zip"], default="url")
    
    blueprint = {}
    source_target = ""

    if source_type == "url":
        source_target = Prompt.ask("Enter Website URL (e.g. https://example.com)")
        console.print("[dim]Inspecting URL...[/dim]")
        try:
            blueprint = iOSAppInspector.inspect_url(source_target)
        except Exception as e:
            console.print(f"[red]Warning: {e}[/red]")
    elif source_type == "folder":
        source_target = Prompt.ask("Enter folder path")
        blueprint = iOSAppInspector.inspect_directory(Path(source_target))
    elif source_type == "zip":
        source_target = Prompt.ask("Enter ZIP file path")
        blueprint = iOSAppInspector.inspect_zip(Path(source_target))

    default_name = blueprint.get("app_name", "My iOS App")
    default_bundle = blueprint.get("bundle_id", "com.web2ipa.app")
    default_theme = blueprint.get("theme_color", "#000000")

    app_name = Prompt.ask("App Name", default=default_name)
    bundle_id = Prompt.ask("Bundle Identifier", default=default_bundle)
    version_name = Prompt.ask("Version Name", default="1.0.0")
    orientation = Prompt.ask("Orientation", choices=["sensor", "portrait", "landscape"], default="sensor")
    theme_color = Prompt.ask("Theme Color (Hex)", default=default_theme)

    detected_icon = blueprint.get("icon_path")
    if detected_icon and Path(detected_icon).exists():
        console.print(f"[bold green]✨ Auto-detected Project Logo:[/bold green] [cyan]{Path(detected_icon).name}[/cyan] ({blueprint.get('detection_sources', {}).get('icon', 'Project Asset')})")
    else:
        console.print("[dim]No local logo detected in project. A synthesized Apple monogram squircle will be generated.[/dim]")

    custom_icon = Prompt.ask("Change Logo Picture? (Path to PNG, JPG, SVG, or press Enter to keep auto-detected)", default="")
    icon_path = custom_icon if (custom_icon and Path(custom_icon).exists()) else detected_icon

    console.print("\n[bold cyan]🚀 Starting Build Pipeline...[/bold cyan]\n")
    builder = IPABuilder(log_callback=lambda msg, pct: console.print(f"[bold dim][{pct}%][/bold dim] {msg}"))

    if source_type == "url":
        res = builder.build_from_url(
            url=source_target,
            app_name=app_name,
            bundle_id=bundle_id,
            version_name=version_name,
            screen_orientation=orientation,
            icon_path=icon_path,
            theme_color=theme_color
        )
    else:
        actual_source = source_target
        temp_dir = None
        if source_type == "zip":
            import zipfile, tempfile
            temp_dir = Path(tempfile.mkdtemp(prefix="web2ipa_wiz_"))
            with zipfile.ZipFile(source_target, 'r') as z:
                z.extractall(temp_dir)
            htmls = list(temp_dir.glob("**/*.html"))
            actual_source = str(htmls[0].parent if htmls else temp_dir)

        try:
            res = builder.build_from_directory(
                source_dir=actual_source,
                app_name=app_name,
                bundle_id=bundle_id,
                version_name=version_name,
                screen_orientation=orientation,
                icon_path=icon_path,
                theme_color=theme_color
            )
        finally:
            if temp_dir and temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)

    if res.get("success"):
        display_success_and_serve(res)

def main():
    parser = argparse.ArgumentParser(description="Web2IPA AI Studio & Compiler")
    parser.add_argument("--gui", "-g", action="store_true", help="Launch Web Studio GUI Dashboard")
    parser.add_argument("--mobile", "-m", action="store_true", help="Display Project Chhaya mobile access QR code and connection links")
    parser.add_argument("--wizard", "-w", action="store_true", help="Launch Interactive Terminal Wizard")
    parser.add_argument("--dir", "-d", type=str, help="Convert local web directory or ZIP to iOS App")
    parser.add_argument("--url", "-u", type=str, help="Convert live website URL to iOS App")
    parser.add_argument("--name", "-n", type=str, default="iOS App", help="Application display name")
    parser.add_argument("--bundle-id", "-b", type=str, default="com.web2ipa.app", help="iOS Bundle Identifier")
    parser.add_argument("--version", "-v", type=str, default="1.0.0", help="Version name")
    parser.add_argument("--theme", type=str, default="#000000", help="Hex theme color")
    parser.add_argument("--orientation", type=str, default="sensor", choices=["sensor", "portrait", "landscape"])
    parser.add_argument("--icon", type=str, help="Path to custom app icon (PNG or SVG)")
    parser.add_argument("--watch", action="store_true", help="Run dropzone watcher on ~/Web2IPA_Dropzone")
    parser.add_argument("--growth", action="store_true", help="Show Agent evolution and memory")
    parser.add_argument("--self-heal", type=str, help="Run self-healer diagnostics on folder")
    parser.add_argument("--inspect", type=str, help="Inspect website URL, ZIP or directory")
    parser.add_argument("--port", "-p", type=int, default=8992, help="Port for GUI or QR Server")

    args = parser.parse_args()

    if args.growth:
        show_growth_memory()
        return

    if args.self_heal:
        run_self_heal(args.self_heal)
        return

    if args.inspect:
        run_inspect(args.inspect)
        return

    if args.watch:
        print_banner()
        start_dropzone_watcher()
        return

    if args.mobile:
        print_banner()
        from web2ipa.mobile_access import MobileAccessManager
        mgr = MobileAccessManager.get_instance(port=args.port)
        mgr.print_terminal_banner()
        return

    if args.gui:
        print_banner()
        start_server(port=args.port)
        return

    if args.wizard:
        run_interactive_wizard()
        return

    if args.url:
        print_banner()
        builder = IPABuilder(log_callback=lambda msg, pct: console.print(f"[bold dim][{pct}%][/bold dim] {msg}"))
        res = builder.build_from_url(
            url=args.url,
            app_name=args.name,
            bundle_id=args.bundle_id,
            version_name=args.version,
            screen_orientation=args.orientation,
            icon_path=args.icon,
            theme_color=args.theme
        )
        if res.get("success"):
            display_success_and_serve(res, default_port=args.port)
        return

    if args.dir:
        print_banner()
        builder = IPABuilder(log_callback=lambda msg, pct: console.print(f"[bold dim][{pct}%][/bold dim] {msg}"))
        res = builder.build_from_directory(
            source_dir=args.dir,
            app_name=args.name,
            bundle_id=args.bundle_id,
            version_name=args.version,
            screen_orientation=args.orientation,
            icon_path=args.icon,
            theme_color=args.theme
        )
        if res.get("success"):
            display_success_and_serve(res, default_port=args.port)
        return

    # Default to wizard if no argument supplied
    print_banner()
    run_interactive_wizard()

if __name__ == "__main__":
    main()
