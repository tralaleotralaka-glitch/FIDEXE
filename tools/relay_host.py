"""The "laptop is a hundred kilometres away" half of the CI test.

Connects to the same public MQTT broker the phone uses, answers the encrypted
requests on the phone's topic and writes a line per request to /tmp/relay.log.
It plays the role of the desktop relay client when the local network is gone:

    python tools/relay_host.py            # creds come from FIDEXE_RELAY_* env
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import paho.mqtt.client as mqtt  # noqa: E402

from app.core.relay_proto import decrypt, encrypt, topics  # noqa: E402

LOG = Path("/tmp/relay.log")
LINK_ID = os.environ.get("FIDEXE_RELAY_ID", "ci-relay-demo-link")
LINK_KEY = os.environ.get("FIDEXE_RELAY_KEY", "6f" * 32)
RAW_BROKERS = os.environ.get("FIDEXE_RELAY_BROKERS", "broker.hivemq.com:8883")
BROKERS = []
for item in RAW_BROKERS.split(","):
    if ":" in item:
        host, _, port = item.partition(":")
        BROKERS.append((host.strip(), int(port)))
KEY = bytes.fromhex(LINK_KEY)
PLAIN = os.environ.get("FIDEXE_RELAY_PLAIN") == "1"   # local tests use a plain broker
TOPICS = topics(LINK_ID)
TOKEN = os.environ.get("FIDEXE_DEMO_TOKEN", "demo-token-for-ci")

APPS = [
    {"pid": 4242, "app": "notepad.exe", "title": "Блокнот — далеко", "active": True},
]
CLOSED: list[int] = []


def log(line: str) -> None:
    stamp = time.strftime("%H:%M:%S")
    text = f"[relay] {stamp} {line}"
    print(text, flush=True)
    try:
        with LOG.open("a", encoding="utf-8") as handle:
            handle.write(text + "\n")
    except OSError:
        pass


def png_frame() -> bytes:
    """Tiny PNG so the phone can decode something even far away."""
    import struct
    import zlib

    width, height = 8, 8
    raw = b"".join(b"\x00" + bytes([120, 108, 255]) * width for _ in range(height))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


FRAME = png_frame()


def handle(op: str, payload: dict, token: str) -> tuple[dict, str]:
    if op == "ping":
        return {"ok": True, "host": "DESKTOP-DEMO", "version": "2.3.0"}, "ping"
    if token != TOKEN:
        raise PermissionError("Сессия истекла, войдите заново")
    if op == "status":
        return ({
            "host": "DESKTOP-DEMO",
            "today_seconds": 15840,
            "current_app": "chrome.exe",
            "current_title": "FIDEXE — через интернет",
            "top_apps": [{"app": "chrome.exe", "seconds": 5400}],
            "clip_count": 42,
            "paused": False,
            "tracking": True,
            "locked_supported": True,
        }, "status")
    if op == "command":
        cmd = str(payload.get("cmd", ""))
        if cmd == "lock":
            log("LOCK COMMAND RECEIVED OVER THE INTERNET")
            return {"ok": True, "cmd": cmd}, "lock"
        if cmd in {"sleep", "pause", "resume"}:
            return {"ok": True, "cmd": cmd}, cmd
        raise ValueError("Неизвестная команда")
    if op == "apps":
        live = [app for app in APPS if app["pid"] not in CLOSED]
        return {"apps": live, "supported": True, "host": "DESKTOP-DEMO"}, "apps"
    if op == "close":
        pid = int(payload.get("pid", 0))
        if pid <= 0:
            raise ValueError("Неизвестное приложение")
        CLOSED.append(pid)
        log(f"CLOSE APP OVER THE INTERNET pid={pid}")
        return {"ok": True, "pid": pid}, "close"
    if op == "camera":
        if payload.get("meta"):
            return ({"supported": True, "allowed": True, "active": True,
                     "width": 8, "height": 8, "fps": 4, "error": ""}, "camera info")
        import base64

        log("CAMERA FRAME OVER THE INTERNET")
        return ({"jpeg": base64.b64encode(FRAME).decode("ascii"),
                 "mime": "image/png", "bytes": len(FRAME)}, "camera frame")
    raise ValueError("Неизвестная операция")


def main() -> int:
    LOG.write_text("", encoding="utf-8")
    log(f"starting, link={LINK_ID[:6]}… brokers={BROKERS}")
    while True:
        for host, port in BROKERS:
            client = mqtt.Client(client_id=f"relay-host-{uuid.uuid4().hex[:6]}", clean_session=True)
            try:
                if not PLAIN:
                    client.tls_set()
                client.connect(host, port, keepalive=45)
            except Exception as exc:  # noqa: BLE001
                log(f"broker {host}:{port} failed: {exc}")
                continue
            client.subscribe(TOPICS["up"], qos=1)

            def on_message(_client, _userdata, message) -> None:
                try:
                    request = decrypt(KEY, message.payload.decode("ascii"))
                except Exception as exc:  # noqa: BLE001
                    log(f"bad message dropped: {exc}")
                    return
                op = str(request.get("op", ""))
                payload = request.get("p") if isinstance(request.get("p"), dict) else {}
                reply = {"v": 1, "id": str(request.get("id", ""))}
                try:
                    data, label = handle(op, payload, str(request.get("t", "")))
                    reply.update({"ok": True, "p": data})
                    log(f"{label.upper()} ANSWERED")
                except PermissionError as exc:
                    reply.update({"ok": False, "e": str(exc), "c": 401})
                    log(f"{op.upper()} REFUSED: {exc}")
                except Exception as exc:  # noqa: BLE001
                    reply.update({"ok": False, "e": str(exc), "c": 400})
                    log(f"{op.upper()} ERROR: {exc}")
                try:
                    client.publish(TOPICS["down"], encrypt(KEY, reply), qos=1)
                except Exception as exc:  # noqa: BLE001
                    log(f"publish failed: {exc}")

            client.on_message = on_message
            client.publish(TOPICS["presence"], json.dumps({"v": 1, "up": True, "host": "DESKTOP-DEMO"}),
                           qos=1, retain=True)
            log(f"READY on {host}:{port}")
            try:
                client.loop_forever(retry_first_connection=False)
            except Exception as exc:  # noqa: BLE001
                log(f"loop stopped: {exc}")
            time.sleep(3)
        time.sleep(5)


if __name__ == "__main__":
    raise SystemExit(main())
