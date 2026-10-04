"""Apify-backed provider.

Actors (override via env if you prefer others):
  TikTok:    clockworks/tiktok-scraper         (hashtags -> videos)
  Instagram: apify/instagram-hashtag-scraper   (hashtags -> posts)
             apify/instagram-reel-scraper      (usernames -> reels)

Apify has no "trending feed", so "trending" = the videos behind a list of seed hashtags
(TRENDSCOPE_SEED_TAGS). Pick seeds for your niche.

Field names were taken from public actor docs and parsers accept several variants;
if an actor changes its output, adjust the parse_* functions below.
"""
import os
from datetime import datetime, timezone
from typing import Any

import httpx

from app.models import Video
from app.providers.base import Provider

API = "https://api.apify.com/v2"
DEFAULT_SEEDS = "fyp,viral,trending"


def _first(d: dict, *keys: str, default: Any = None) -> Any:
    for k in keys:
        if d.get(k) is not None:
            return d[k]
    return default


def _int(x: Any) -> int:
    try:
        return int(x or 0)
    except (TypeError, ValueError):
        return 0


def _dt(x: Any) -> datetime:
    if isinstance(x, (int, float)):
        return datetime.fromtimestamp(x, tz=timezone.utc)
    if isinstance(x, str):
        try:
            d = datetime.fromisoformat(x.replace("Z", "+00:00"))
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _tags(raw: Any) -> list[str]:
    out = []
    for t in raw or []:
        name = t.get("name") if isinstance(t, dict) else t
        if name:
            out.append(str(name).lstrip("#").lower())
    return out


def parse_tiktok(item: dict) -> Video | None:
    if not item.get("id"):
        return None
    author = item.get("authorMeta") or {}
    music = item.get("musicMeta") or {}
    return Video(
        id=str(item["id"]),
        platform="tiktok",
        author=str(_first(author, "name", "nickName", default="unknown")),
        caption=item.get("text") or "",
        hashtags=_tags(item.get("hashtags")),
        sound=music.get("musicName"),
        posted_at=_dt(_first(item, "createTimeISO", "createTime")),
        views=_int(item.get("playCount")),
        likes=_int(item.get("diggCount")),
        comments=_int(item.get("commentCount")),
        shares=_int(item.get("shareCount")),
        author_followers=_int(author.get("fans")),
    )


def parse_instagram(item: dict) -> Video | None:
    vid = _first(item, "id", "reelId", "shortCode")
    if not vid:
        return None
    music = item.get("musicInfo") or {}
    caption = item.get("caption") or ""
    return Video(
        id=str(vid),
        platform="instagram",
        author=str(_first(item, "ownerUsername", "username", default="unknown")),
        caption=caption,
        hashtags=_tags(item.get("hashtags")) or [w[1:].lower() for w in caption.split() if w.startswith("#") and len(w) > 1],
        sound=_first(music, "song_name", "songName", "audio_id"),
        posted_at=_dt(item.get("timestamp")),
        views=_int(_first(item, "videoPlayCount", "videoViewCount", "viewsCount")),
        likes=_int(item.get("likesCount")),
        comments=_int(item.get("commentsCount")),
        shares=_int(item.get("sharesCount")),
        author_followers=_int(_first(item, "ownerFollowersCount", "followersCount")),
    )


class ApifyProvider(Provider):
    name = "apify"

    def __init__(self, token: str | None = None, client: httpx.Client | None = None):
        self.token = token or os.getenv("APIFY_TOKEN")
        if not self.token:
            raise RuntimeError("APIFY_TOKEN is not set")
        self.client = client or httpx.Client(timeout=300)
        self.tiktok_actor = os.getenv("APIFY_TIKTOK_ACTOR", "clockworks/tiktok-scraper")
        self.ig_actor = os.getenv("APIFY_IG_HASHTAG_ACTOR", "apify/instagram-hashtag-scraper")
        self.seeds = [s.strip().lstrip("#") for s in os.getenv("TRENDSCOPE_SEED_TAGS", DEFAULT_SEEDS).split(",") if s.strip()]

    def _run(self, actor: str, payload: dict) -> list[dict]:
        """Run an actor synchronously and return its dataset items."""
        url = f"{API}/acts/{actor.replace('/', '~')}/run-sync-get-dataset-items"
        r = self.client.post(url, json=payload, headers={"Authorization": f"Bearer {self.token}"})
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []

    def fetch_hashtag(self, platform: str, tag: str, limit: int = 100) -> list[Video]:
        tag = tag.lstrip("#")
        if platform == "tiktok":
            items = self._run(self.tiktok_actor, {"hashtags": [tag], "resultsPerPage": limit})
            parse = parse_tiktok
        elif platform == "instagram":
            items = self._run(self.ig_actor, {"hashtags": [tag], "resultsType": "reels", "resultsLimit": limit})
            parse = parse_instagram
        else:
            raise ValueError(platform)
        return [v for v in (parse(i) for i in items) if v]

    def fetch_trending(self, platform: str, limit: int = 100) -> list[Video]:
        per_tag = max(limit // max(len(self.seeds), 1), 1)
        seen: dict[str, Video] = {}
        for tag in self.seeds:
            for v in self.fetch_hashtag(platform, tag, per_tag):
                seen[v.id] = v
        return list(seen.values())
