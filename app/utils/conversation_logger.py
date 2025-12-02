import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import aiofiles
from app.configs.settings import settings


async def log_event(session_id: str, event: str, payload: Dict[str, Any]) -> None:
    logs_dir = Path(settings.conversation_logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"{session_id}.jsonl"
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event": event,
        "payload": payload,
    }
    async with aiofiles.open(log_path, "a", encoding="utf-8") as handle:
        await handle.write(json.dumps(entry, ensure_ascii=False))
        await handle.write("\n")

