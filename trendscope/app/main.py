import logging
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app import analytics
from app.providers import get_provider
from app.storage import Store

log = logging.getLogger("trendscope")
store = Store(os.getenv("TRENDSCOPE_DB", "trendscope.db"))
PLATFORMS = {"tiktok", "instagram"}


def _refresh_all() -> None:
    """Refresh every platform; one failing platform must not stop the others."""
    for platform in sorted(PLATFORMS):
        try:
            store.save(get_provider().fetch_trending(platform, int(os.getenv("TRENDSCOPE_REFRESH_LIMIT", "100"))))
            log.info("scheduled refresh ok: %s", platform)
        except Exception:
            log.exception("scheduled refresh failed: %s", platform)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """TRENDSCOPE_REFRESH_HOURS=6 refreshes all platforms every 6 hours. Unset/0 = off."""
    stop = threading.Event()
    hours = float(os.getenv("TRENDSCOPE_REFRESH_HOURS", "0") or 0)
    if hours > 0:
        def loop():
            while not stop.wait(hours * 3600):
                _refresh_all()
        threading.Thread(target=loop, daemon=True).start()
    yield
    stop.set()


app = FastAPI(title="TrendScope", lifespan=lifespan)


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


def _check(platform: str) -> str:
    if platform not in PLATFORMS:
        raise HTTPException(400, f"platform must be one of {sorted(PLATFORMS)}")
    return platform


@app.post("/refresh/{platform}")
def refresh(platform: str, limit: int = 100, hashtag: str | None = None):
    """Pull fresh data from the configured provider and store it."""
    _check(platform)
    try:
        p = get_provider()
    except (RuntimeError, ValueError) as e:
        raise HTTPException(500, str(e))
    try:
        videos = p.fetch_hashtag(platform, hashtag, limit) if hashtag else p.fetch_trending(platform, limit)
    except Exception as e:  # provider/network failure
        raise HTTPException(502, f"Provider error: {e}")
    store.save(videos)
    return {"provider": p.name, "saved": len(videos)}


@app.get("/trends/{platform}")
def trends(platform: str):
    videos = store.load(_check(platform))
    growth = store.growth(platform)
    return {
        "videos_analyzed": len(videos),
        "snapshots": store.snapshot_count(platform),
        "fastest_growing": analytics.fastest_growing(videos, growth),
        "hashtag_momentum": analytics.hashtag_momentum(videos, growth),
        "top_hashtags": analytics.top_hashtags(videos),
        "rising_hashtags": analytics.rising_hashtags(videos),
        "top_sounds": analytics.top_sounds(videos),
        "best_posting_hours": analytics.best_posting_hours(videos),
        "breakout_videos": [
            {**v.model_dump(mode="json"), "virality": round(analytics.virality_score(v), 2)}
            for v in analytics.breakout_videos(videos)
        ],
    }
