from __future__ import annotations

from pathlib import Path
import json
import uuid
from datetime import datetime

INSTANCE_FILE = Path("data/runtime/instance.json")

def get_or_create_instance_id() -> str:
    INSTANCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if INSTANCE_FILE.exists():
        try:
            data = json.loads(INSTANCE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("instance_id"):
                return str(data["instance_id"])
        except Exception:
            pass
    instance_id = str(uuid.uuid4())
    payload = {"instance_id": instance_id, "created_at": datetime.utcnow().isoformat() + "Z"}
    INSTANCE_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return instance_id
