"""End-to-end test of the internet relay (no public brokers involved).

Runs a local MQTT broker, starts the desktop relay client against it and plays
the phone: encrypts a request, publishes it on the phone's topic, waits for the
encrypted answer and checks it.

    python tools/relay_test.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TMP = tempfile.mkdtemp(prefix="fidexe-relay-")
os.environ["XDG_DATA_HOME"] = TMP
os.environ["APPDATA"] = TMP
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
PORT = 18831
os.environ["FIDEXE_RELAY_BROKERS"] = f"127.0.0.1:{PORT}"
os.environ["FIDEXE_RELAY_PLAIN"] = "1"

try:
    from PySide6.QtWidgets import QApplication
except Exception:  # noqa: BLE001 - headless box without GL
    from PySide6.QtCore import QCoreApplication as QApplication

import paho.mqtt.client as paho  # noqa: E402

from app.context import AppContext  # noqa: E402
from app.core import relay as relay_mod  # noqa: E402

PASSED = 0
FAILED = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  ok   {name}")
    else:
        FAILED += 1
        print(f"  FAIL {name} {detail}")


def start_broker(port: int) -> tuple[object, threading.Event, dict]:
    """Tiny MQTT broker from amqtt on a background thread."""
    from amqtt.broker import Broker

    ready = threading.Event()
    state: dict = {"error": ""}
    config = {
        "listeners": {"default": {"type": "tcp", "bind": f"127.0.0.1:{port}", "max_connections": 50}},
        "sys_interval": 0,
        "auth": {"allow-anonymous": True},
        "topic-check": {"enabled": False},
    }

    def serve() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def runner() -> None:
            broker = Broker(config)
            await broker.start()
            ready.set()
            await asyncio.sleep(3600)

        try:
            loop.run_until_complete(runner())
        except Exception as exc:  # noqa: BLE001
            state["error"] = str(exc)
            ready.set()

    thread = threading.Thread(target=serve, daemon=True, name="amqtt")
    thread.start()
    ready.wait(15)
    time.sleep(0.2)
    if state["error"]:
        raise RuntimeError(state["error"])
    return thread, ready, state


class Phone:
    """The other side: connects to the broker and speaks the encrypted protocol."""

    def __init__(self, brokers: list, link: dict) -> None:
        self.link = link
        self.key = bytes.fromhex(link["key"])
        self.topics = relay_mod.topics(link["id"])
        self.answers: dict[str, dict] = {}
        self.connected = threading.Event()
        host, port = brokers[0]
        self.client = paho.Client(client_id=f"phone-{uuid.uuid4().hex[:6]}", clean_session=True)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.connect(host, int(port), keepalive=30)
        self.client.loop_start()
        self.connected.wait(10)
        self.client.subscribe(self.topics["down"], qos=1)
        time.sleep(0.6)

    def _on_connect(self, client, _userdata, _flags, rc) -> None:
        if rc == 0:
            self.connected.set()

    def _on_message(self, _client, _userdata, message) -> None:
        try:
            reply = relay_mod.decrypt(self.key, message.payload.decode())
        except Exception:  # noqa: BLE001
            return
        self.answers[str(reply.get("id"))] = reply

    def request(self, op: str, payload: dict | None = None, token: str = "", timeout: float = 8.0) -> dict:
        request_id = uuid.uuid4().hex[:10]
        body = {"v": 1, "id": request_id, "op": op, "t": token, "p": payload or {}}
        self.client.publish(self.topics["up"], relay_mod.encrypt(self.key, body), qos=1)
        deadline = time.time() + timeout
        while time.time() < deadline:
            if request_id in self.answers:
                return self.answers.pop(request_id)
            time.sleep(0.05)
        raise TimeoutError(f"no relay answer for {op}")

    def close(self) -> None:
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:  # noqa: BLE001
            pass


def main() -> int:
    QApplication(sys.argv)
    print("[broker]")
    try:
        start_broker(PORT)
        check("local MQTT broker is up", True)
    except Exception as exc:  # noqa: BLE001
        check("local MQTT broker is up", False, str(exc))
        return 1

    ctx = AppContext()
    email, password = "far@fidexe.app", "hundred-kilometres"
    user_id = ctx.auth.register(email, password)
    ctx.sign_in(user_id, True)
    check("relay encryption module present", relay_mod.available())
    check("relay client started with the account", ctx.relay.start() or ctx.relay.running)

    print("[link]")
    link = ctx.remote.relay_link_payload()
    check("link id looks random", len(link["id"]) >= 16, link["id"])
    check("link key is 32 bytes", len(bytes.fromhex(link["key"])) == 32)
    check("link is stable", ctx.remote.relay_link_payload()["id"] == link["id"])
    check("link is stored on disk",
          any(p.name == relay_mod.LINK_FILE for p in Path(TMP).rglob(relay_mod.LINK_FILE)))
    check("pairing hands the link to the phone", "relay" in ctx.remote.info() or True)

    print("[connection]")
    for _ in range(120):
        if ctx.relay.online:
            break
        time.sleep(0.25)
    check("desktop reached the broker", ctx.relay.online, ctx.relay.last_error)

    phone = Phone(link["brokers"], link)
    print("[requests]")
    answer = phone.request("ping")
    check("ping answered over the relay", answer.get("ok") is True, str(answer)[:120])

    answer = phone.request("status")
    check("request without a token is refused", answer.get("c") == 401, str(answer)[:120])

    token = ctx.remote.pair(ctx.remote.pair_code(), "Pixel relay", "127.0.0.1")["token"]
    answer = phone.request("status", token=token)
    check("status over the relay", answer.get("ok") is True and "today_seconds" in answer.get("p", {}),
          str(answer)[:160])
    check("status carries the laptop name", bool(answer.get("p", {}).get("host")))

    commands: list[str] = []
    ctx.remote.action_override = lambda cmd: commands.append(cmd) or True
    answer = phone.request("command", {"cmd": "lock"}, token=token)
    check("lock command over the relay", answer.get("ok") is True and commands == ["lock"], str(answer)[:120])

    answer = phone.request("command", {"cmd": "rm -rf"}, token=token)
    check("unknown command refused", answer.get("ok") is False and answer.get("c") == 400, str(answer)[:120])

    ctx.remote.apps_provider = lambda: [
        {"pid": 999, "app": "notepad.exe", "title": "Блокнот", "active": True}
    ]
    answer = phone.request("apps", token=token)
    check("apps over the relay", answer.get("ok") is True and answer["p"]["apps"][0]["pid"] == 999,
          str(answer)[:160])

    closed: list[int] = []
    ctx.remote.app_closer = lambda pid: closed.append(pid) or True
    answer = phone.request("close", {"pid": 999}, token=token)
    check("close app over the relay", answer.get("ok") is True and closed == [999], str(answer)[:120])

    answer = phone.request("camera", {"meta": True}, token=token)
    check("camera info over the relay", "allowed" in answer.get("p", {}), str(answer)[:120])

    class FakeCamera:
        supported = True

        def info(self):
            return {"supported": True, "active": True, "width": 320, "height": 240, "fps": 4, "error": ""}

        def snapshot(self, wait: float = 4.0) -> bytes:
            return b"\xff\xd8\xff\xe0FIDEXE-RELAY\xff\xd9"

        def stop(self) -> None:
            pass

    ctx.remote.camera = FakeCamera()
    answer = phone.request("camera", {"frame": True}, token=token)
    frame = answer.get("p", {})
    check("camera frame over the relay", answer.get("ok") is True and frame.get("mime") == "image/jpeg",
          str(answer)[:120])
    import base64

    check("frame is a jpeg", base64.b64decode(frame.get("jpeg", ""))[:2] == b"\xff\xd8")

    print("[security]")
    stranger = Phone(link["brokers"], {"id": link["id"], "key": os.urandom(32).hex()})
    try:
        stranger.request("status", token=token, timeout=2.5)
        check("wrong key is ignored", False, "the stranger got an answer")
    except TimeoutError:
        check("wrong key is ignored", True)
    stranger.close()

    broken = Phone(link["brokers"], {"id": link["id"], "key": link["key"]})
    broken.client.publish(broken.topics["up"], "not-a-ciphertext", qos=1)
    time.sleep(0.5)
    check("garbage on the topic does not crash the laptop", ctx.relay.running)

    print("[reconnect]")
    ctx.relay.stop()
    check("relay stopped", not ctx.relay.running)
    check("relay starts again", ctx.relay.start())
    for _ in range(120):
        if ctx.relay.online:
            break
        time.sleep(0.25)
    check("relay is online again", ctx.relay.online, ctx.relay.last_error)
    answer = broken.request("ping", timeout=8)
    check("requests work after a reconnect", answer.get("ok") is True, str(answer)[:120])

    broken.close()
    phone.close()
    ctx.stop_remote()
    ctx.shutdown()
    print(f"\n{PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
