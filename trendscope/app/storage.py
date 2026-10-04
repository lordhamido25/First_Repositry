import sqlite3
import threading
from datetime import datetime, timedelta, timezone

from app.models import Video


class Store:
    def __init__(self, path: str = "trendscope.db"):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.Lock()  # the scheduler thread and requests share this connection
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS videos (platform TEXT, id TEXT, data TEXT, "
            "PRIMARY KEY (platform, id))"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS snapshots (platform TEXT, id TEXT, captured_at TEXT, "
            "views INTEGER, likes INTEGER, comments INTEGER, shares INTEGER)"
        )
        self.db.execute("CREATE INDEX IF NOT EXISTS snap_idx ON snapshots (platform, id, captured_at)")

    def save(self, videos: list[Video], captured_at: datetime | None = None) -> None:
        """Upsert the videos and record a snapshot of their current numbers."""
        ts = (captured_at or datetime.now(timezone.utc)).isoformat()
        with self.lock:
            self.db.executemany(
                "INSERT OR REPLACE INTO videos VALUES (?, ?, ?)",
                [(v.platform, v.id, v.model_dump_json()) for v in videos],
            )
            self.db.executemany(
                "INSERT INTO snapshots VALUES (?, ?, ?, ?, ?, ?, ?)",
                [(v.platform, v.id, ts, v.views, v.likes, v.comments, v.shares) for v in videos],
            )
            self.db.commit()

    def load(self, platform: str | None = None) -> list[Video]:
        q, args = "SELECT data FROM videos", ()
        if platform:
            q, args = q + " WHERE platform = ?", (platform,)
        with self.lock:
            rows = self.db.execute(q, args).fetchall()
        return [Video.model_validate_json(r[0]) for r in rows]

    def growth(self, platform: str, window_hours: int = 48) -> list[dict]:
        """Per-video view gain between its first and last snapshot in the window.

        Only videos with at least two snapshots at different times are returned.
        """
        since = (datetime.now(timezone.utc) - timedelta(hours=window_hours)).isoformat()
        with self.lock:
            rows = self.db.execute(
                "SELECT id, captured_at, views FROM snapshots "
                "WHERE platform = ? AND captured_at >= ? ORDER BY id, captured_at",
                (platform, since),
            ).fetchall()
        by_id: dict[str, list[tuple[str, int]]] = {}
        for vid, ts, views in rows:
            by_id.setdefault(vid, []).append((ts, views))
        out = []
        for vid, snaps in by_id.items():
            (t0, v0), (t1, v1) = snaps[0], snaps[-1]
            hours = (datetime.fromisoformat(t1) - datetime.fromisoformat(t0)).total_seconds() / 3600
            if hours <= 0:
                continue
            out.append({"id": vid, "gain": v1 - v0, "hours": round(hours, 2),
                        "views_per_hour": round((v1 - v0) / hours, 1)})
        return out

    def snapshot_count(self, platform: str) -> int:
        with self.lock:
            return self.db.execute(
                "SELECT COUNT(DISTINCT captured_at) FROM snapshots WHERE platform = ?", (platform,)
            ).fetchone()[0]
