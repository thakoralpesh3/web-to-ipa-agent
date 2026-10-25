import os
import time
import shutil
import zipfile
import subprocess
from pathlib import Path
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    Observer = None
    FileSystemEventHandler = object
    HAS_WATCHDOG = False

from .builder import IPABuilder

DROPZONE_DIR = Path.home() / "Web2IPA_Dropzone"
OUTPUT_DIR = Path.home() / "Web2IPA_Output"

def send_notification(title: str, message: str):
    try:
        subprocess.run(["notify-send", "-i", "applications-other", title, message], check=False)
    except Exception:
        pass

class DropzoneHandler(FileSystemEventHandler):
    """
    Auto-detects newly dropped website folders or ZIP files and converts them to iOS Apps.
    """

    def __init__(self):
        self.processed = set()
        self.builder = IPABuilder(log_callback=self._log)

    def _log(self, msg: str, pct: int):
        print(f"[Dropzone {pct}%] {msg}")

    def on_created(self, event):
        path = Path(event.src_path)
        
        if path.name.startswith(".") or path.name.endswith(".tmp") or str(path) in self.processed:
            return

        time.sleep(1.5)
        if not path.exists():
            return

        if path.is_file() and path.suffix.lower() == ".zip":
            self.processed.add(str(path))
            self._process_zip(path)
        elif path.is_dir():
            self.processed.add(str(path))
            self._process_directory(path)

    def _process_zip(self, zip_path: Path):
        app_name = zip_path.stem.replace("-", " ").replace("_", " ").title()
        send_notification("Web2IPA Agent", f"🍎 Processing ZIP: {app_name}...")
        
        extract_dir = DROPZONE_DIR / f"_temp_{zip_path.stem}"
        try:
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(extract_dir)

            html_files = list(extract_dir.glob("**/*.html"))
            source_dir = html_files[0].parent if html_files else extract_dir

            clean_pkg = f"com.web2ipa.{zip_path.stem.lower()[:20]}"
            res = self.builder.build_from_directory(
                source_dir=str(source_dir),
                app_name=app_name,
                bundle_id=clean_pkg
            )

            if res["success"]:
                send_notification("Web2IPA Agent", f"🎉 Generated {res['ipa_name']} & {res['mobileconfig_name']}!")
        except Exception as e:
            print(f"[Dropzone] Error processing ZIP {zip_path}: {e}")
        finally:
            if extract_dir.exists():
                shutil.rmtree(extract_dir, ignore_errors=True)

    def _process_directory(self, dir_path: Path):
        app_name = dir_path.name.replace("-", " ").replace("_", " ").title()
        send_notification("Web2IPA Agent", f"🍎 Processing Directory: {app_name}...")
        clean_pkg = f"com.web2ipa.{dir_path.name.lower()[:20]}"
        try:
            res = self.builder.build_from_directory(
                source_dir=str(dir_path),
                app_name=app_name,
                bundle_id=clean_pkg
            )
            if res["success"]:
                send_notification("Web2IPA Agent", f"🎉 Generated {res['ipa_name']} & {res['mobileconfig_name']}!")
        except Exception as e:
            print(f"[Dropzone] Error processing directory {dir_path}: {e}")

def start_dropzone_watcher():
    """Starts file watcher on ~/Web2IPA_Dropzone."""
    DROPZONE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not HAS_WATCHDOG:
        print("[Web2IPA] 'watchdog' library not found. Running polling loop...")
        handler = DropzoneHandler()
        known = set(os.listdir(DROPZONE_DIR))
        while True:
            time.sleep(2)
            current = set(os.listdir(DROPZONE_DIR))
            new_items = current - known
            for item in new_items:
                path = DROPZONE_DIR / item
                if path.is_file() and path.suffix.lower() == ".zip":
                    handler._process_zip(path)
                elif path.is_dir() and not item.startswith("_temp"):
                    handler._process_directory(path)
            known = current

    event_handler = DropzoneHandler()
    observer = Observer()
    observer.schedule(event_handler, str(DROPZONE_DIR), recursive=False)
    observer.start()
    print(f"[Web2IPA] 👁️ Watching Dropzone: {DROPZONE_DIR}")
    print(f"[Web2IPA] 📂 Output Directory: {OUTPUT_DIR}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
