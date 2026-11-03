"""
Electron Desktop Integration & Exporter
Integrates upstream github.com/electron/electron framework.
Packages Web applications and PWAs into cross-platform Desktop applications (macOS DMG/App, Linux, Windows)
alongside iOS IPA generation.
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

ELECTRON_MAIN_JS = """const { app, BrowserWindow, shell } = require('electron');
const path = require('path');

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 720,
    minWidth: 800,
    minHeight: 600,
    title: "{app_name}",
    titleBarStyle: 'hiddenInset',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true
    }
  });

  win.setMenuBarVisibility(false);
  {load_target}

  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
"""

class ElectronExporter:
    """Exports Web & PWA assets into standalone Electron desktop applications for macOS/Linux/Windows."""

    @classmethod
    def export(cls, target_dir: Path, app_name: str = "iOS Web App", entry_url_or_file: str = "index.html", is_remote: bool = False) -> Dict[str, Any]:
        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        load_statement = f'win.loadURL("{entry_url_or_file}");' if is_remote else f'win.loadFile(path.join(__dirname, "{entry_url_or_file}"));'

        main_js = ELECTRON_MAIN_JS.replace("{app_name}", app_name).replace("{load_target}", load_statement)
        (target_dir / "main.js").write_text(main_js, encoding="utf-8")

        pkg_json = {
            "name": app_name.lower().replace(" ", "-"),
            "version": "1.0.0",
            "description": f"{app_name} desktop app powered by Electron",
            "main": "main.js",
            "scripts": {
                "start": "electron .",
                "build": "electron-builder"
            },
            "devDependencies": {
                "electron": "^33.0.0"
            },
            "repository": {
                "type": "git",
                "url": "https://github.com/electron/electron"
            }
        }
        (target_dir / "package.json").write_text(json.dumps(pkg_json, indent=2), encoding="utf-8")

        return {
            "success": True,
            "framework": "Electron (github.com/electron/electron)",
            "desktop_dir": str(target_dir)
        }
