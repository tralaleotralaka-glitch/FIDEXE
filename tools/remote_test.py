"""End-to-end test of the LAN remote-control API (the Android app speaks this).

    QT_QPA_PLATFORM=offscreen python tools/remote_test.py
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import socket
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TMP = tempfile.mkdtemp(prefix="fidexe-remote-")
os.environ["XDG_DATA_HOME"] = TMP
os.environ["APPDATA"] = TMP
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:  # a GUI is not required for the protocol test
    from PySide6.QtWidgets import QApplication  # noqa: E402
except Exception:  # noqa: BLE001 - headless box without GL/dbus
    from PySide6.QtCore import QCoreApplication as QApplication  # noqa: E402

from app.context import AppContext  # noqa: E402
from app.core import remote as remote_mod  # noqa: E402

PORT = 47899
BASE = f"http://127.0.0.1:{PORT}"
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


def request(path: str, payload: dict | None = None, token: str = "", method: str | None = None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method or ("POST" if data else "GET"))
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode() or "{}")


def request_raw(path: str, token: str = ""):
    """Fetch a binary endpoint: returns (status, content-type, body)."""
    req = urllib.request.Request(BASE + path)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, response.headers.get("Content-Type", ""), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type", ""), exc.read()


def derive(password: str, salt_hex: str, iterations: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), iterations).hex()


def prove(password_hash: str, challenge: str) -> str:
    return hmac.new(bytes.fromhex(password_hash), challenge.encode(), hashlib.sha256).hexdigest()


def main() -> int:
    app = QApplication(sys.argv)
    ctx = AppContext()
    email, password = "phone@fidexe.app", "correct-horse-1"
    user_id = ctx.auth.register(email, password)
    ctx.sign_in(user_id, True)

    print("[desktop server]")
    check("server starts together with the account", ctx.remote.running)
    ctx.stop_remote()
    ctx.settings.set("remote_port", PORT)
    commands: list[str] = []
    ctx.remote.action_override = lambda cmd: commands.append(cmd) or True
    check("server starts", ctx.set_remote_enabled(True))
    check("status running", ctx.remote.running)

    code, info = request("/api/info")
    check("info responds", code == 200, str(code))
    check("masked account", info.get("accounts") == ["ph***@fidexe.app"], str(info.get("accounts")))
    check("protocol version", info.get("protocol") == 1)
    check("host name present", bool(info.get("host")))

    code, ping = request("/api/ping")
    check("ping ok", code == 200 and ping.get("ok") is True)

    print("[authentication]")
    code, challenge = request("/api/auth/challenge", {"email": email})
    check("challenge issued", code == 200 and "challenge" in challenge, str(challenge))
    pw_hash = derive(password, challenge["salt"], challenge["iterations"])

    code, bad = request(
        "/api/auth/proof",
        {"email": email, "challenge": challenge["challenge"], "proof": "00" * 32, "device": "Pixel test"},
    )
    check("wrong proof rejected", code == 400, str(code))

    code, challenge = request("/api/auth/challenge", {"email": email})
    pw_hash = derive(password, challenge["salt"], challenge["iterations"])
    code, auth = request(
        "/api/auth/proof",
        {
            "email": email,
            "challenge": challenge["challenge"],
            "proof": prove(pw_hash, challenge["challenge"]),
            "device": "Pixel 7 (тест)",
        },
    )
    check("correct proof accepted", code == 200 and "token" in auth, str(auth))
    token = auth.get("token", "")
    check("token ttl", auth.get("expires_in", 0) > 0)

    code, reused = request(
        "/api/auth/proof",
        {
            "email": email,
            "challenge": challenge["challenge"],
            "proof": prove(pw_hash, challenge["challenge"]),
            "device": "Pixel 7",
        },
    )
    check("challenge is single use", code == 400 and "error" in reused, f"{code} {reused}")

    check("unknown account", request("/api/auth/challenge", {"email": "nobody@x.y"})[0] == 400)

    print("[pairing code]")
    current = ctx.remote.pair_code()
    check("code is six digits", len(current) == 6 and current.isdigit(), current)
    check("code formatted for display", remote_mod.format_pair_code(current) == f"{current[:3]} {current[3:]}")
    check("code rotates within a minute", 1 <= ctx.remote.pair_remaining() <= 60, str(ctx.remote.pair_remaining()))
    secret = ctx.remote.pair_secret()
    window = ctx.remote.pair_window()
    check("code changes every minute",
          len({remote_mod.pair_code_for(secret, window + i) for i in range(6)}) == 6)
    check("info advertises pairing", info.get("pairing") is True and info.get("pair_code_ttl") == 60)

    code, paired = request("/api/pair", {"code": "000000", "device": "Pixel code"})
    check("wrong code rejected", code == 400 and "error" in paired, f"{code} {paired}")
    code, paired = request("/api/pair", {"code": "12ab", "device": "Pixel code"})
    check("short code rejected", code == 400, str(code))

    code, paired = request("/api/pair", {"code": current, "device": "Pixel 8 (код)"})
    check("correct code accepted", code == 200 and "token" in paired, f"{code} {paired}")
    code_token = paired.get("token", "")
    check("pair response carries account", paired.get("account") == email, str(paired))
    code, status2 = request("/api/status", token=code_token)
    check("code token opens the panel", code == 200 and "today_seconds" in status2, str(code))

    previous = remote_mod.pair_code_for(secret, window - 1)
    code, _ = request("/api/pair", {"code": previous, "device": "Pixel old"})
    check("code from the previous minute still works", code == 200, str(code))

    stale = remote_mod.pair_code_for(secret, window - 3)
    code, _ = request("/api/pair", {"code": stale, "device": "Pixel stale"})
    check("code from three minutes ago rejected", code == 400, str(code))

    code, paired = request("/api/pair", {"code": remote_mod.format_pair_code(current), "device": "Pixel spaced"})
    check("code with a space accepted", code == 200, str(code))

    print("[authorised calls]")
    code, status = request("/api/status", token=token)
    check("status authorised", code == 200, str(code))
    for key in ("today_seconds", "current_app", "top_apps", "clip_count", "paused", "host"):
        check(f"status has {key}", key in status, str(status.keys()))

    check("no token -> 401", request("/api/status")[0] == 401)
    check("bad token -> 401", request("/api/status", token="nope")[0] == 401)

    code, result = request("/api/command", {"cmd": "lock"}, token=token)
    check("lock command accepted", code == 200 and result.get("ok") is True, str(result))
    check("lock executed once", commands == ["lock"], str(commands))
    code, result = request("/api/command", {"cmd": "sleep"}, token=token)
    check("sleep command accepted", code == 200)
    code, result = request("/api/command", {"cmd": "format_disk"}, token=token)
    check("unknown command rejected", code == 400, str(code))

    print("[signals]")
    seen: list[tuple[str, str]] = []
    ctx.remote.command_done.connect(lambda cmd, dev: seen.append((cmd, dev)))
    request("/api/command", {"cmd": "pause"}, token=token)
    app.processEvents()
    check("signal emitted", ("pause", "Pixel 7 (тест)") in seen, str(seen))

    print("[rate limiting]")
    # the wrong/short/stale attempts above already count against this client
    locked_out = False
    for _ in range(10):
        code, body = request("/api/pair", {"code": "000000", "device": "brute"})
        if code == 400 and "Слишком много" in str(body.get("error", "")):
            locked_out = True
            break
    check("brute force is rate limited", locked_out)

    print("[running apps]")
    check("apps need auth", request("/api/apps")[0] == 401)
    code, listing = request("/api/apps", token=token)
    check("apps endpoint responds", code == 200 and "apps" in listing, str(listing)[:120])
    check("apps supported flag", isinstance(listing.get("supported"), bool))

    ctx.remote.apps_provider = lambda: [
        {"pid": 4242, "app": "notepad.exe", "title": "Блокнот — заметки", "active": True},
        {"pid": 4343, "app": "chrome.exe", "title": "GitHub", "active": False},
    ]
    closed: list[int] = []
    ctx.remote.app_closer = lambda pid: closed.append(pid) or True
    code, listing = request("/api/apps", token=token)
    check("apps listed", code == 200 and len(listing["apps"]) == 2, str(listing)[:120])
    check("first app is the active one", listing["apps"][0]["app"] == "notepad.exe")
    check("apps marked supported", listing.get("supported") is True)

    code, result = request("/api/apps/close", {"pid": 4242}, token=token)
    check("close accepted", code == 200 and result.get("ok") is True, str(result))
    check("close used the pid", closed == [4242], str(closed))
    check("close needs auth", request("/api/apps/close", {"pid": 4242})[0] == 401)
    check("close with bad pid rejected", request("/api/apps/close", {"pid": 0}, token=token)[0] == 400)
    check("close with text pid rejected",
          request("/api/apps/close", {"pid": "nope"}, token=token)[0] == 400)

    ctx.remote.app_closer = None
    code, result = request("/api/apps/close", {"pid": 4242}, token=token)
    check("close refused when unsupported", code == 400 and "Windows" in str(result.get("error")), str(result))

    print("[camera]")
    check("camera needs auth", request("/api/camera/info")[0] == 401)
    code, info_cam = request("/api/camera/info", token=token)
    check("camera info responds", code == 200 and "allowed" in info_cam, str(info_cam))
    check("camera allowed right after sign-in", info_cam.get("allowed") is True, str(info_cam))
    status, _ctype, _body = request_raw("/api/camera/frame", token=token)
    check("frame errors cleanly without a webcam", status == 403, str(status))

    class FakeCamera:
        supported = True

        def info(self):
            return {"supported": True, "active": True, "width": 640, "height": 480, "fps": 8, "error": ""}

        def snapshot(self, wait: float = 4.0) -> bytes:
            return b"\xff\xd8\xff\xe0FIDEXE-FAKE-JPEG\xff\xd9"

        def stop(self) -> None:
            pass

    ctx.remote.camera = FakeCamera()
    code, info_cam = request("/api/camera/info", token=token)
    check("camera stays allowed", info_cam.get("allowed") is True, str(info_cam))
    check("camera reports resolution", info_cam.get("width") == 640 and info_cam.get("height") == 480)
    status, ctype, body = request_raw("/api/camera/frame", token=token)
    check("frame delivered", status == 200 and ctype.startswith("image/jpeg"), f"{status} {ctype}")
    check("frame looks like a jpeg", body.startswith(b"\xff\xd8") and body.endswith(b"\xff\xd9"), str(body[:8]))
    check("frame needs auth", request_raw("/api/camera/frame")[0] == 401)

    print("[discovery]")
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    probe.settimeout(3.0)
    try:
        probe.sendto(b"FIDEXE?", ("127.0.0.1", remote_mod.DISCOVERY_PORT))
        reply, _ = probe.recvfrom(4096)
    except OSError as exc:
        reply = b""
        check("UDP discovery answers", False, str(exc))
    else:
        found = json.loads(reply.decode("utf-8"))
        check("UDP discovery answers", found.get("app") == "FIDEXE", str(found)[:120])
        check("UDP discovery reports the port", found.get("port") == PORT, str(found.get("port")))
        check("UDP discovery reports the laptop", bool(found.get("host")), str(found.get("host")))
        check("UDP discovery reports an address", ":" in str(found.get("address", "")), str(found.get("address")))
        check("UDP discovery lists the LAN ips", isinstance(found.get("ips"), list) and found["ips"],
              str(found.get("ips")))
    finally:
        probe.close()
    check("firewall state is known",
          ctx.remote.firewall_state in {"ok", "created", "blocked", "skipped"},
          ctx.remote.firewall_state)

    print("[a paired phone survives a restart]")
    keep_token = code_token
    ctx.set_remote_enabled(False)
    check("server stopped for the restart", not ctx.remote.running)
    check("server starts again", ctx.set_remote_enabled(True))
    code, status_after = request("/api/status", token=keep_token)
    check("old phone token still works after restart", code == 200, f"{code} {status_after}")
    check("sessions are stored on disk", (Path(TMP) / "FIDEXE" / "remote_sessions.json").exists()
          or any(p.name == "remote_sessions.json" for p in Path(TMP).rglob("remote_sessions.json")))

    print("[teardown]")
    ctx.set_remote_enabled(False)
    check("server stopped", not ctx.remote.running)
    try:
        request("/api/ping")
        closed = False
    except urllib.error.URLError:
        closed = True
    check("port closed after stop", closed)
    ctx.shutdown()

    print(f"\n{PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
