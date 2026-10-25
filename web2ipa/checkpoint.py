import os
import json
import time
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

CHECKPOINTS_DIR = Path.home() / ".web2ipa" / "checkpoints"

class CheckpointManager:
    """
    Manages atomic state journaling, checkpoints, and crash recovery for iOS builds.
    Ensures that if a conversion is interrupted at any stage, it can resume
    exactly from where it stopped.
    """

    STAGES = [
        "INIT",
        "STAGED",
        "SELF_HEALED",
        "CODE_PATCHED",
        "PROJECT_GENERATED",
        "ICONS_GENERATED",
        "PACKAGED",
        "COMPLETED"
    ]

    @classmethod
    def init_checkpoint(cls, session_id: str, params: Dict[str, Any], workspace_dir: str) -> Dict[str, Any]:
        CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)
        checkpoint_file = CHECKPOINTS_DIR / f"{session_id}.json"

        data = {
            "session_id": session_id,
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
            "stage": "INIT",
            "params": params,
            "workspace_dir": str(workspace_dir),
            "repairs_made": [],
            "detected_permissions": [],
            "framework": "Vanilla HTML5",
            "completed": False
        }

        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return data

    @classmethod
    def commit_stage(cls, session_id: str, stage: str, updates: Optional[Dict[str, Any]] = None):
        checkpoint_file = CHECKPOINTS_DIR / f"{session_id}.json"
        if not checkpoint_file.exists():
            return

        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            data["stage"] = stage
            data["updated_at"] = int(time.time())
            if updates:
                for k, v in updates.items():
                    data[k] = v

            if stage == "COMPLETED":
                data["completed"] = True

            with open(checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[CheckpointManager] Error committing stage {stage}: {e}")

    @classmethod
    def get_interrupted_sessions(cls) -> List[Dict[str, Any]]:
        if not CHECKPOINTS_DIR.exists():
            return []

        interrupted = []
        for cf in CHECKPOINTS_DIR.glob("*.json"):
            try:
                with open(cf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not data.get("completed", False):
                    ws = Path(data.get("workspace_dir", ""))
                    if ws.exists():
                        interrupted.append(data)
                    else:
                        cf.unlink()
            except Exception:
                pass

        return interrupted

    @classmethod
    def remove_checkpoint(cls, session_id: str):
        checkpoint_file = CHECKPOINTS_DIR / f"{session_id}.json"
        if checkpoint_file.exists():
            try:
                checkpoint_file.unlink()
            except Exception:
                pass
