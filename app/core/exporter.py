"""CSV / JSON export of the collected data."""
from __future__ import annotations

import csv
import json
from datetime import date, datetime, timedelta
from pathlib import Path

from .db import Storage


def export_usage_csv(store: Storage, user_id: int, path: Path, days: int = 30) -> int:
    end = int(datetime.combine(date.today(), datetime.max.time()).timestamp())
    start = int(datetime.combine(date.today() - timedelta(days=days - 1), datetime.min.time()).timestamp())
    rows = store.export_usage_rows(user_id, start, end)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(["дата", "время", "приложение", "окно", "секунд"])
        count = 0
        for row in rows:
            moment = datetime.fromtimestamp(int(row["ts"]))
            writer.writerow([moment.strftime("%d.%m.%Y"), moment.strftime("%H:%M:%S"), row["process"], row["title"], row["seconds"]])
            count += 1
    return count


def export_clipboard_csv(store: Storage, user_id: int, path: Path) -> int:
    rows = store.export_clip_rows(user_id)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(["дата", "тип", "содержимое", "файл", "закреплено"])
        count = 0
        for row in rows:
            moment = datetime.fromtimestamp(int(row["created_at"]))
            writer.writerow([
                moment.strftime("%d.%m.%Y %H:%M:%S"),
                row["kind"],
                (row["content"] or "").replace("\r", " ").replace("\n", " ")[:2000],
                row["image_path"] or "",
                "да" if row["pinned"] else "нет",
            ])
            count += 1
    return count


def export_json(store: Storage, user_id: int, path: Path, email: str = "") -> int:
    payload = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "account": email,
        "clipboard": [
            {
                "created_at": datetime.fromtimestamp(int(r["created_at"])).isoformat(timespec="seconds"),
                "kind": r["kind"],
                "content": r["content"],
                "image_path": r["image_path"],
                "pinned": bool(r["pinned"]),
            }
            for r in store.export_clip_rows(user_id)
        ],
        "usage": [
            {
                "ts": datetime.fromtimestamp(int(r["ts"])).isoformat(timespec="seconds"),
                "process": r["process"],
                "title": r["title"],
                "seconds": r["seconds"],
            }
            for r in store.export_usage_rows(user_id, 0, 2**31 - 1)
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(payload["clipboard"]) + len(payload["usage"])
