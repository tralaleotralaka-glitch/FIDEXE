import json
import os
import platform
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any

import psutil
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

if getattr(sys, "frozen", False):
    BUNDLE_DIR = Path(sys._MEIPASS)
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BUNDLE_DIR = Path(__file__).resolve().parent
    BASE_DIR = BUNDLE_DIR

STATIC_DIR = BUNDLE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
NOTES_FILE = DATA_DIR / "notes.json"

DATA_DIR.mkdir(exist_ok=True)
if not NOTES_FILE.exists():
    NOTES_FILE.write_text(json.dumps({"notes": [], "tasks": []}, ensure_ascii=False, indent=2), encoding="utf-8")

app = FastAPI(title="LapPulse — Центр управления ноутбуком")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def format_uptime(seconds: float) -> str:
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}д")
    if hours:
        parts.append(f"{hours}ч")
    parts.append(f"{minutes}м")
    return " ".join(parts)


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.2)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/system")
def system_stats() -> dict[str, Any]:
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_freq = psutil.cpu_freq()
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net = psutil.net_io_counters()
    boot_time = psutil.boot_time()
    uptime = time.time() - boot_time

    battery_info: dict[str, Any] | None = None
    try:
        bat = psutil.sensors_battery()
        if bat is not None:
            battery_info = {
                "percent": round(bat.percent, 1),
                "power_plugged": bat.power_plugged,
                "secsleft": bat.secsleft if bat.secsleft not in (-1, -2) else None,
            }
    except Exception:
        battery_info = None

    return {
        "hostname": socket.gethostname(),
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
        "local_ip": get_local_ip(),
        "uptime": format_uptime(uptime),
        "cpu": {
            "percent": round(cpu_percent, 1),
            "cores_logical": psutil.cpu_count(logical=True),
            "cores_physical": psutil.cpu_count(logical=False),
            "freq_mhz": round(cpu_freq.current, 0) if cpu_freq else None,
        },
        "memory": {
            "percent": round(mem.percent, 1),
            "used_gb": round(mem.used / (1024**3), 2),
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
        },
        "disk": {
            "percent": round(disk.percent, 1),
            "used_gb": round(disk.used / (1024**3), 2),
            "total_gb": round(disk.total / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
        },
        "network": {
            "sent_mb": round(net.bytes_sent / (1024**2), 1),
            "recv_mb": round(net.bytes_recv / (1024**2), 1),
        },
        "battery": battery_info,
    }


@app.get("/api/processes")
def list_processes(limit: int = Query(15, ge=1, le=50), q: str = Query("")) -> list[dict[str, Any]]:
    procs = []
    q_lower = q.strip().lower()
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
        try:
            info = p.info
            name = info.get("name") or ""
            if q_lower and q_lower not in name.lower():
                continue
            procs.append(
                {
                    "pid": info["pid"],
                    "name": name,
                    "cpu": round(info.get("cpu_percent") or 0.0, 1),
                    "memory": round(info.get("memory_percent") or 0.0, 1),
                    "status": info.get("status") or "",
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    procs.sort(key=lambda x: (x["cpu"], x["memory"]), reverse=True)
    return procs[:limit]


class DiskScanRequest(BaseModel):
    path: str = str(Path.home())
    limit: int = 15


@app.post("/api/disk-scan")
def disk_scan(req: DiskScanRequest) -> dict[str, Any]:
    target = Path(req.path).expanduser().resolve()
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=400, detail="Указанная папка не существует")

    items: list[dict[str, Any]] = []
    try:
        for entry in os.scandir(target):
            try:
                if entry.is_file(follow_symlinks=False):
                    size = entry.stat(follow_symlinks=False).st_size
                    items.append({"name": entry.name, "type": "file", "size_bytes": size})
                elif entry.is_dir(follow_symlinks=False):
                    dir_size = 0
                    file_count = 0
                    for root, _, files in os.walk(entry.path, followlinks=False):
                        for f in files:
                            try:
                                fp = os.path.join(root, f)
                                dir_size += os.path.getsize(fp)
                                file_count += 1
                                if file_count > 5000:
                                    break
                            except OSError:
                                continue
                        if file_count > 5000:
                            break
                    items.append({"name": entry.name, "type": "dir", "size_bytes": dir_size})
            except OSError:
                continue
    except PermissionError:
        raise HTTPException(status_code=403, detail="Нет доступа к папке")

    items.sort(key=lambda x: x["size_bytes"], reverse=True)
    return {
        "path": str(target),
        "items": items[: req.limit],
    }


class NotesPayload(BaseModel):
    notes: list[dict[str, Any]]
    tasks: list[dict[str, Any]]


@app.get("/api/notes")
def get_notes() -> dict[str, Any]:
    try:
        return json.loads(NOTES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"notes": [], "tasks": []}


@app.post("/api/notes")
def save_notes(payload: NotesPayload) -> dict[str, str]:
    NOTES_FILE.write_text(
        json.dumps(payload.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    def open_browser() -> None:
        time.sleep(1.2)
        webbrowser.open("http://127.0.0.1:8000")

    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1" if getattr(sys, "frozen", False) else "0.0.0.0", port=8000, reload=False)
