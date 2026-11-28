"""Internet relay: keeps the encrypted channel to the phone open.

The phone and the laptop both dial *out* to a public MQTT broker over TLS, so
there is no port forwarding, no firewall hole, no fixed IP and no server of our
own.  Everything that travels through the broker is encrypted end to end
(AES-256-GCM) with a key created when the phone was paired over the local
network: the broker sees a random topic name and a blob of ciphertext.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time

from PySide6.QtCore import QObject, Signal

from .paths import APP_VERSION
from .relay_proto import (  # noqa: F401 - re-exported for the app and the tests
    AESGCM,
    BROKERS,
    KEEPALIVE,
    LINK_FILE,
    MAX_REMOTE_BODY,
    PLAIN_TCP,
    PROTOCOL,
    TOPIC_ROOT,
    available,
    decrypt,
    encrypt,
    link_payload,
    load_link,
    topics,
)

log = logging.getLogger(__name__)

# ----------------------------------------------------------------------- client
class RelayClient(QObject):
    """Keeps an encrypted control channel open through a public broker."""

    state_changed = Signal(str)   # online | offline | unavailable

    def __init__(self, remote, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.remote = remote
        self._thread: threading.Thread | None = None
        self._client = None
        self._running = False
        self._link: dict = {}
        self._topic: dict[str, str] = {}
        self._state = "offline"
        self._lock = threading.Lock()
        self.last_error = ""
        self.requests_served = 0

    # ------------------------------------------------------------------ state
    @property
    def state(self) -> str:
        return self._state

    @property
    def online(self) -> bool:
        return self._state == "online"

    @property
    def running(self) -> bool:
        return self._running

    @property
    def broker(self) -> str:
        client = self._client
        host = getattr(client, "_host", "") if client is not None else ""
        port = getattr(client, "_port", "") if client is not None else ""
        return f"{host}:{port}" if host else ""

    def _set_state(self, state: str) -> None:
        if state != self._state:
            self._state = state
            log.info("Интернет-связь с телефоном: %s", state)
            self.state_changed.emit(state)

    # -------------------------------------------------------------- lifecycle
    def start(self) -> bool:
        if not available():
            self.last_error = "нет модуля шифрования cryptography"
            log.warning("Интернет-связь недоступна: %s", self.last_error)
            self._set_state("unavailable")
            return False
        if self._running:
            return True
        try:
            import paho.mqtt.client as mqtt  # noqa: F401
        except Exception:  # noqa: BLE001 - optional dependency
            self.last_error = "нет модуля paho-mqtt"
            log.warning("Интернет-связь недоступна: %s", self.last_error)
            self._set_state("unavailable")
            return False
        self._link = link_payload()
        self._topic = topics(self._link["id"])
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="fidexe-relay")
        self._thread.start()
        return True

    def stop(self) -> None:
        self._running = False
        client = self._client
        self._client = None
        if client is not None:
            try:
                client.publish(self._topic.get("presence", "fidexe"), json.dumps({"v": PROTOCOL, "up": False}),
                               qos=1, retain=True)
                time.sleep(0.05)
            except Exception:  # noqa: BLE001
                pass
            try:
                client.disconnect()
                client.loop_stop()
            except Exception:  # noqa: BLE001
                pass
        self._set_state("offline")

    # ----------------------------------------------------------------- worker
    def _key(self) -> bytes:
        return bytes.fromhex(self._link["key"])

    def _run(self) -> None:
        import paho.mqtt.client as mqtt

        while self._running:
            for host, port in self._link.get("brokers") or BROKERS:
                if not self._running:
                    return
                client = mqtt.Client(client_id=f"fidexe-{os.urandom(4).hex()}", clean_session=True)
                client.reconnect_delay_set(min_delay=2, max_delay=30)
                client.on_connect = self._on_connect
                client.on_message = self._on_message
                client.on_disconnect = self._on_disconnect
                try:
                    if not PLAIN_TCP:
                        client.tls_set()
                    client._host = host  # type: ignore[attr-defined]
                    client._port = port  # type: ignore[attr-defined]
                    log.info("Интернет-связь: подключаюсь к %s:%s", host, port)
                    client.connect(host, port, keepalive=KEEPALIVE)
                except Exception as exc:  # noqa: BLE001 - try the next broker
                    log.info("Интернет-связь: %s:%s не отвечает (%s)", host, port, exc)
                    try:
                        client.loop_stop()
                    except Exception:  # noqa: BLE001
                        pass
                    continue
                with self._lock:
                    self._client = client
                try:
                    client.loop_forever(retry_first_connection=False)
                except Exception as exc:  # noqa: BLE001
                    log.info("Интернет-связь прервана: %s", exc)
                finally:
                    with self._lock:
                        if self._client is client:
                            self._client = None
                    try:
                        client.loop_stop()
                    except Exception:  # noqa: BLE001
                        pass
                self._set_state("offline")
            if self._running:
                time.sleep(5)

    # ------------------------------------------------------------- paho hooks
    def _on_connect(self, client, _userdata, _flags, rc) -> None:
        if rc != 0:
            self.last_error = f"брокер отказал: код {rc}"
            log.warning("Интернет-связь: %s", self.last_error)
            try:
                client.disconnect()
            except Exception:  # noqa: BLE001
                pass
            return
        client.subscribe(self._topic["up"], qos=1)
        client.publish(
            self._topic["presence"],
            json.dumps({"v": PROTOCOL, "up": True, "ts": int(time.time()),
                        "host": self.remote_host(), "ver": APP_VERSION}),
            qos=1,
            retain=True,
        )
        self.last_error = ""
        self._set_state("online")

    def _on_disconnect(self, _client, _userdata, rc) -> None:
        if rc != 0:
            self._set_state("offline")

    def remote_host(self) -> str:
        try:
            return str(self.remote.hostname())  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            return ""

    def _on_message(self, client, _userdata, message) -> None:
        try:
            request = decrypt(self._key(), message.payload.decode("ascii", "strict"))
        except Exception as exc:  # noqa: BLE001 - garbage or a foreign message
            log.debug("Интернет-связь: сообщение отброшено (%s)", exc)
            return
        request_id = str(request.get("id", ""))
        op = str(request.get("op", ""))
        token = str(request.get("t", ""))
        payload = request.get("p") if isinstance(request.get("p"), dict) else {}
        reply: dict = {"v": PROTOCOL, "id": request_id}
        try:
            data = self.remote.relay_dispatch(op, payload, token)
            reply["ok"] = True
            reply["p"] = data
        except Exception as exc:  # noqa: BLE001 - auth and business errors alike
            code = getattr(exc, "code", 0)
            reply["ok"] = False
            reply["e"] = str(exc) or exc.__class__.__name__
            reply["c"] = code
            if code == 401:
                log.info("Интернет-связь: телефон просит новый код (%s)", exc)
        try:
            client.publish(self._topic["down"], encrypt(self._key(), reply), qos=1)
            self.requests_served += 1
        except Exception:  # noqa: BLE001
            log.exception("Интернет-связь: не удалось отправить ответ")
