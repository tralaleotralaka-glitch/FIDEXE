"""Wire format of the internet relay: topics, encryption, the shared link.

Kept free of Qt and of the application package on purpose: the CI relay host and
the tests load this file directly to play the phone.

Wire format (one MQTT message per request/response)::

    <nonce>.<ciphertext+tag>      both parts base64url, no padding

Topics, all derived from a random per-installation link id::

    fidexe/v2/<id>/u      phone -> laptop requests
    fidexe/v2/<id>/d      laptop -> phone answers
    fidexe/v2/<id>/s      laptop presence (retained)
"""
from __future__ import annotations

import base64
import json
import logging
import os
import secrets

from .paths import APP_VERSION, data_dir

log = logging.getLogger(__name__)

try:  # the relay is optional: the LAN path keeps working without it
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except Exception:  # noqa: BLE001 - missing dependency or broken wheel
    AESGCM = None  # type: ignore[assignment]

DEFAULT_BROKERS: tuple[tuple[str, int], ...] = (
    ("broker.hivemq.com", 8883),
    ("broker.emqx.io", 8883),
    ("test.mosquitto.org", 8883),
)


def _brokers_from_env() -> tuple[tuple[str, int], ...]:
    """`FIDEXE_RELAY_BROKERS=host:port,host:port` overrides the public brokers."""
    raw = os.environ.get("FIDEXE_RELAY_BROKERS", "").strip()
    parsed: list[tuple[str, int]] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk or ":" not in chunk:
            continue
        host, _, port = chunk.partition(":")
        try:
            parsed.append((host.strip(), int(port)))
        except ValueError:
            continue
    return tuple(parsed) or DEFAULT_BROKERS


BROKERS: tuple[tuple[str, int], ...] = _brokers_from_env()
PLAIN_TCP = os.environ.get("FIDEXE_RELAY_PLAIN") == "1"   # tests use a local broker
LINK_FILE = "relay_link.json"
TOPIC_ROOT = "fidexe/v2"
PROTOCOL = 1
AAD = b"fidexe-relay-v1"
KEEPALIVE = 45
MAX_REMOTE_BODY = 900 * 1024   # one camera frame in base64 fits comfortably


# --------------------------------------------------------------------- crypto
def available() -> bool:
    return AESGCM is not None


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def encrypt(key: bytes, payload: dict) -> str:
    if AESGCM is None:
        raise RuntimeError("relay encryption is unavailable")
    nonce = os.urandom(12)
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(raw) > MAX_REMOTE_BODY:
        raise RuntimeError("payload too large for the relay")
    sealed = AESGCM(key).encrypt(nonce, raw, AAD)
    return f"{_b64e(nonce)}.{_b64e(sealed)}"


def decrypt(key: bytes, message: str) -> dict:
    if AESGCM is None:
        raise RuntimeError("relay encryption is unavailable")
    try:
        nonce_text, sealed_text = str(message).split(".", 1)
        raw = AESGCM(key).decrypt(_b64d(nonce_text), _b64d(sealed_text), AAD)
    except Exception as exc:  # noqa: BLE001 - wrong key or broken message
        raise ValueError(f"relay payload rejected: {exc}") from None
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("relay payload is not an object")
    return data


def topics(link_id: str) -> dict[str, str]:
    return {
        "up": f"{TOPIC_ROOT}/{link_id}/u",
        "down": f"{TOPIC_ROOT}/{link_id}/d",
        "presence": f"{TOPIC_ROOT}/{link_id}/s",
    }


# ------------------------------------------------------------------ link file
def load_link() -> dict:
    """The pairing key shared with the phone; created on first use."""
    path = data_dir() / LINK_FILE
    data: dict = {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    link_id = str(data.get("id") or "")
    key_hex = str(data.get("key") or "")
    if len(link_id) < 16 or len(key_hex) != 64:
        link_id = _b64e(secrets.token_bytes(16))
        key_hex = secrets.token_bytes(32).hex()
        try:
            path.write_text(json.dumps({"id": link_id, "key": key_hex}), encoding="utf-8")
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
        except OSError:
            log.warning("Не удалось сохранить ключ интернет-связи")
    return {"id": link_id, "key": key_hex}


def link_payload() -> dict:
    """What the phone needs to reach this laptop from anywhere."""
    link = load_link()
    return {
        "id": link["id"],
        "key": link["key"],
        "brokers": [[host, port] for host, port in BROKERS],
        "protocol": PROTOCOL,
        "version": APP_VERSION,
    }


