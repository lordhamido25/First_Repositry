import sqlite3

from app.models import Video


class Store:
    def __init__(self, path: str = "trendscope.db"):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS videos (platform TEXT, id TEXT, data TEXT, "
            "PRIMARY KEY (platform, id))"
        )

    def save(self, videos: list[Video]) -> None:
        self.db.executemany(
            "INSERT OR REPLACE INTO videos VALUES (?, ?, ?)",
            [(v.platform, v.id, v.model_dump_json()) for v in videos],
        )
        self.db.commit()

    def load(self, platform: str | None = None) -> list[Video]:
        q, args = "SELECT data FROM videos", ()
        if platform:
            q, args = q + " WHERE platform = ?", (platform,)
        return [Video.model_validate_json(r[0]) for r in self.db.execute(q, args)]
