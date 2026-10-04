import os

from fastapi import FastAPI, HTTPException

from app import analytics
from app.providers import get_provider
from app.storage import Store

app = FastAPI(title="TrendScope")
store = Store(os.getenv("TRENDSCOPE_DB", "trendscope.db"))
PLATFORMS = {"tiktok", "instagram"}


def _check(platform: str) -> str:
    if platform not in PLATFORMS:
        raise HTTPException(400, f"platform must be one of {sorted(PLATFORMS)}")
    return platform


@app.post("/refresh/{platform}")
def refresh(platform: str, limit: int = 100, hashtag: str | None = None):
    """Pull fresh data from the configured provider and store it."""
    _check(platform)
    p = get_provider()
    videos = p.fetch_hashtag(platform, hashtag, limit) if hashtag else p.fetch_trending(platform, limit)
    store.save(videos)
    return {"provider": p.name, "saved": len(videos)}


@app.get("/trends/{platform}")
def trends(platform: str):
    videos = store.load(_check(platform))
    return {
        "videos_analyzed": len(videos),
        "top_hashtags": analytics.top_hashtags(videos),
        "rising_hashtags": analytics.rising_hashtags(videos),
        "top_sounds": analytics.top_sounds(videos),
        "best_posting_hours": analytics.best_posting_hours(videos),
        "breakout_videos": [
            {**v.model_dump(mode="json"), "virality": round(analytics.virality_score(v), 2)}
            for v in analytics.breakout_videos(videos)
        ],
    }
