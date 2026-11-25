"""SQLite storage: users, clipboard history and foreground-app usage."""
from __future__ import annotations

import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from .paths import db_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    email       TEXT NOT NULL UNIQUE,
    pw_hash     TEXT NOT NULL,
    salt        TEXT NOT NULL,
    created_at  INTEGER NOT NULL,
    last_login  INTEGER
);

CREATE TABLE IF NOT EXISTS clipboard (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    kind       TEXT NOT NULL,          -- text | link | image | code
    content    TEXT,
    image_path TEXT,
    created_at INTEGER NOT NULL,
    pinned     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_clip_user ON clipboard(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS usage (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id  INTEGER NOT NULL,
    ts       INTEGER NOT NULL,
    day      TEXT NOT NULL,
    process  TEXT NOT NULL,
    title    TEXT,
    seconds  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_usage_user_day ON usage(user_id, day);
CREATE INDEX IF NOT EXISTS idx_usage_ts ON usage(ts);
CREATE UNIQUE INDEX IF NOT EXISTS idx_usage_bucket ON usage(user_id, ts, process);
"""


@dataclass(slots=True)
class ClipEntry:
    id: int
    kind: str
    content: str
    image_path: str
    created_at: int
    pinned: bool

    @property
    def when(self) -> datetime:
        return datetime.fromtimestamp(self.created_at)


@dataclass(slots=True)
class AppSlice:
    process: str
    seconds: int


class Storage:
    """Thread-safe thin wrapper around sqlite3."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or db_path()
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.commit()

    # ---------------------------------------------------------------- users
    def create_user(self, email: str, pw_hash: str, salt: str) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO users(email, pw_hash, salt, created_at, last_login) VALUES (?,?,?,?,?)",
                (email.lower(), pw_hash, salt, int(time.time()), int(time.time())),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def find_user(self, email: str) -> sqlite3.Row | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM users WHERE email = ?", (email.lower(),)
            ).fetchone()
            return row

    def user_by_id(self, user_id: int) -> sqlite3.Row | None:
        with self._lock:
            return self._conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    def touch_login(self, user_id: int) -> None:
        with self._lock:
            self._conn.execute("UPDATE users SET last_login = ? WHERE id = ?", (int(time.time()), user_id))
            self._conn.commit()

    def emails(self) -> list[str]:
        with self._lock:
            return [r["email"] for r in self._conn.execute("SELECT email FROM users ORDER BY id")]

    def delete_user_data(self, user_id: int) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM clipboard WHERE user_id = ?", (user_id,))
            self._conn.execute("DELETE FROM usage WHERE user_id = ?", (user_id,))
            self._conn.commit()

    # ------------------------------------------------------------ clipboard
    def last_clip(self, user_id: int) -> ClipEntry | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM clipboard WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)
            ).fetchone()
        return self._to_entry(row)

    def add_clip(
        self,
        user_id: int,
        kind: str,
        content: str = "",
        image_path: str = "",
        ts: int | None = None,
    ) -> int | None:
        """Insert a clipboard entry, skipping an immediate duplicate."""
        now = ts or int(time.time())
        with self._lock:
            last = self._conn.execute(
                "SELECT kind, content, image_path FROM clipboard WHERE user_id = ? ORDER BY id DESC LIMIT 1",
                (user_id,),
            ).fetchone()
            if last and last["kind"] == kind and last["content"] == content and last["image_path"] == image_path:
                return None
            cur = self._conn.execute(
                "INSERT INTO clipboard(user_id, kind, content, image_path, created_at) VALUES (?,?,?,?,?)",
                (user_id, kind, content, image_path, now),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def clips(
        self,
        user_id: int,
        *,
        query: str = "",
        kind: str = "all",
        limit: int = 300,
    ) -> list[ClipEntry]:
        sql = "SELECT * FROM clipboard WHERE user_id = ?"
        args: list[object] = [user_id]
        if kind != "all":
            sql += " AND kind = ?"
            args.append(kind)
        if query:
            sql += " AND content LIKE ?"
            args.append(f"%{query}%")
        sql += " ORDER BY pinned DESC, id DESC LIMIT ?"
        args.append(limit)
        with self._lock:
            rows = self._conn.execute(sql, args).fetchall()
        return [e for e in (self._to_entry(r) for r in rows) if e]

    def set_pinned(self, clip_id: int, pinned: bool) -> None:
        with self._lock:
            self._conn.execute("UPDATE clipboard SET pinned = ? WHERE id = ?", (int(pinned), clip_id))
            self._conn.commit()

    def delete_clip(self, clip_id: int) -> None:
        with self._lock:
            row = self._conn.execute("SELECT image_path FROM clipboard WHERE id = ?", (clip_id,)).fetchone()
            self._conn.execute("DELETE FROM clipboard WHERE id = ?", (clip_id,))
            self._conn.commit()
        if row and row["image_path"]:
            try:
                Path(row["image_path"]).unlink(missing_ok=True)
            except OSError:
                pass

    def clear_clips(self, user_id: int, *, keep_pinned: bool = True) -> int:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, image_path FROM clipboard WHERE user_id = ?" + (" AND pinned = 0" if keep_pinned else ""),
                (user_id,),
            ).fetchall()
            sql = "DELETE FROM clipboard WHERE user_id = ?" + (" AND pinned = 0" if keep_pinned else "")
            cur = self._conn.execute(sql, (user_id,))
            self._conn.commit()
        for row in rows:
            if row["image_path"]:
                try:
                    Path(row["image_path"]).unlink(missing_ok=True)
                except OSError:
                    pass
        return cur.rowcount

    def clip_count(self, user_id: int) -> int:
        with self._lock:
            return int(
                self._conn.execute("SELECT COUNT(*) AS c FROM clipboard WHERE user_id = ?", (user_id,)).fetchone()["c"]
            )

    def prune_clips(self, user_id: int, limit: int) -> None:
        if limit <= 0:
            return
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, image_path FROM clipboard WHERE user_id = ? AND pinned = 0 "
                "ORDER BY id DESC LIMIT -1 OFFSET ?",
                (user_id, limit),
            ).fetchall()
            if not rows:
                return
            self._conn.executemany("DELETE FROM clipboard WHERE id = ?", [(r["id"],) for r in rows])
            self._conn.commit()
        for row in rows:
            if row["image_path"]:
                try:
                    Path(row["image_path"]).unlink(missing_ok=True)
                except OSError:
                    pass

    # ---------------------------------------------------------------- usage
    def add_usage(self, user_id: int, process: str, title: str, seconds: int, ts: int | None = None) -> None:
        """Accumulate usage into one-minute buckets to keep the table compact."""
        now = ts or int(time.time())
        bucket = now - now % 60
        day = datetime.fromtimestamp(now).strftime("%Y-%m-%d")
        with self._lock:
            self._conn.execute(
                "INSERT INTO usage(user_id, ts, day, process, title, seconds) VALUES (?,?,?,?,?,?) "
                "ON CONFLICT(user_id, ts, process) DO UPDATE SET "
                "seconds = seconds + excluded.seconds, title = excluded.title",
                (user_id, bucket, day, process, (title or "")[:300], int(seconds)),
            )
            self._conn.commit()

    def daily_totals(self, user_id: int, start_day: date, end_day: date) -> dict[str, int]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT day, SUM(seconds) AS s FROM usage WHERE user_id = ? AND day BETWEEN ? AND ? "
                "GROUP BY day",
                (user_id, start_day.isoformat(), end_day.isoformat()),
            ).fetchall()
        return {r["day"]: int(r["s"] or 0) for r in rows}

    def top_apps(
        self, user_id: int, start_ts: int, end_ts: int, limit: int = 8
    ) -> list[AppSlice]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT process, SUM(seconds) AS s FROM usage "
                "WHERE user_id = ? AND ts BETWEEN ? AND ? AND process <> '' "
                "GROUP BY LOWER(process) ORDER BY s DESC LIMIT ?",
                (user_id, start_ts, end_ts, limit),
            ).fetchall()
        return [AppSlice(r["process"], int(r["s"] or 0)) for r in rows]

    def hourly(self, user_id: int, day: date) -> list[int]:
        start = int(datetime.combine(day, datetime.min.time()).timestamp())
        end = start + 86400
        buckets = [0] * 24
        with self._lock:
            rows = self._conn.execute(
                "SELECT ts, seconds FROM usage WHERE user_id = ? AND ts >= ? AND ts < ?",
                (user_id, start, end),
            ).fetchall()
        for r in rows:
            hour = datetime.fromtimestamp(r["ts"]).hour
            buckets[hour] += int(r["seconds"] or 0)
        return buckets

    def distinct_apps(self, user_id: int, start_ts: int, end_ts: int) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(DISTINCT LOWER(process)) AS c FROM usage "
                "WHERE user_id = ? AND ts BETWEEN ? AND ?",
                (user_id, start_ts, end_ts),
            ).fetchone()
        return int(row["c"] or 0)

    def app_seconds(self, user_id: int, process: str, start_ts: int, end_ts: int) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT SUM(seconds) AS s FROM usage "
                "WHERE user_id = ? AND LOWER(process) = LOWER(?) AND ts BETWEEN ? AND ?",
                (user_id, process, start_ts, end_ts),
            ).fetchone()
        return int(row["s"] or 0)

    def latest_usage(self, user_id: int) -> sqlite3.Row | None:
        with self._lock:
            return self._conn.execute(
                "SELECT * FROM usage WHERE user_id = ? ORDER BY ts DESC, id DESC LIMIT 1", (user_id,)
            ).fetchone()

    def total_seconds(self, user_id: int, start_ts: int, end_ts: int) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT SUM(seconds) AS s FROM usage WHERE user_id = ? AND ts BETWEEN ? AND ?",
                (user_id, start_ts, end_ts),
            ).fetchone()
        return int(row["s"] or 0)

    def app_titles(self, user_id: int, start_ts: int, end_ts: int, limit: int = 6) -> list[tuple[str, int]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT title, SUM(seconds) AS s FROM usage "
                "WHERE user_id = ? AND ts BETWEEN ? AND ? AND title <> '' "
                "GROUP BY title ORDER BY s DESC LIMIT ?",
                (user_id, start_ts, end_ts, limit),
            ).fetchall()
        return [(r["title"], int(r["s"] or 0)) for r in rows]

    def active_days(self, user_id: int, start_ts: int, end_ts: int) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(DISTINCT day) AS c FROM usage WHERE user_id = ? AND ts BETWEEN ? AND ?",
                (user_id, start_ts, end_ts),
            ).fetchone()
        return int(row["c"] or 0)

    def minute_series(self, user_id: int, minutes: int = 60, end_ts: int | None = None) -> list[int]:
        """Seconds per minute bucket for the trailing `minutes` window."""
        end = int(end_ts or time.time())
        end -= end % 60
        start = end - minutes * 60
        buckets = [0] * minutes
        with self._lock:
            rows = self._conn.execute(
                "SELECT ts, seconds FROM usage WHERE user_id = ? AND ts >= ? ORDER BY ts",
                (user_id, start),
            ).fetchall()
        for row in rows:
            idx = int((int(row["ts"]) - start) // 60)
            if 0 <= idx < minutes:
                buckets[idx] += int(row["seconds"] or 0)
        return buckets

    def first_usage_ts(self, user_id: int) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT MIN(ts) AS m FROM usage WHERE user_id = ?", (user_id,)
            ).fetchone()
        return int(row["m"] or 0)

    def oldest_day(self, user_id: int) -> date:
        first = self.first_usage_ts(user_id)
        return datetime.fromtimestamp(first).date() if first else date.today()

    def prune_usage(self, user_id: int, days: int) -> None:
        if days <= 0:
            return
        cutoff = int(time.time()) - days * 86400
        with self._lock:
            self._conn.execute("DELETE FROM usage WHERE user_id = ? AND ts < ?", (user_id, cutoff))
            self._conn.commit()

    def export_usage_rows(self, user_id: int, start_ts: int, end_ts: int) -> Iterable[sqlite3.Row]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT ts, day, process, title, seconds FROM usage "
                "WHERE user_id = ? AND ts BETWEEN ? AND ? ORDER BY ts",
                (user_id, start_ts, end_ts),
            ).fetchall()
        return rows

    def export_clip_rows(self, user_id: int) -> Iterable[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(
                "SELECT created_at, kind, content, image_path, pinned FROM clipboard "
                "WHERE user_id = ? ORDER BY id",
                (user_id,),
            ).fetchall()

    # ---------------------------------------------------------------- misc
    def close(self) -> None:
        with self._lock:
            self._conn.close()

    @staticmethod
    def _to_entry(row: sqlite3.Row | None) -> ClipEntry | None:
        if row is None:
            return None
        return ClipEntry(
            id=int(row["id"]),
            kind=row["kind"],
            content=row["content"] or "",
            image_path=row["image_path"] or "",
            created_at=int(row["created_at"]),
            pinned=bool(row["pinned"]),
        )
