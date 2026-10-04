import random
from datetime import datetime, timedelta, timezone

from app.models import Video
from app.providers.base import Provider

_TAGS = ["fyp", "booktok", "gymtok", "recipe", "travel", "ai", "fashion", "diy", "comedy", "grwm"]
_SOUNDS = ["original sound - a", "viral beat 1", "remix 2", "trending audio 3"]


class MockProvider(Provider):
    """Deterministic fake data so the app runs with no API keys."""

    name = "mock"

    def _make(self, platform: str, n: int, seed: int, tag: str | None = None) -> list[Video]:
        rng = random.Random(seed)
        now = datetime.now(timezone.utc)
        out = []
        for i in range(n):
            followers = rng.randint(500, 2_000_000)
            views = int(followers * rng.uniform(0.05, 6))
            tags = rng.sample(_TAGS, k=rng.randint(1, 4))
            if tag and tag not in tags:
                tags.append(tag)
            out.append(
                Video(
                    id=f"{platform}-{seed}-{i}",
                    platform=platform,
                    author=f"creator{rng.randint(1, 60)}",
                    caption=f"video {i}",
                    hashtags=tags,
                    sound=rng.choice(_SOUNDS),
                    posted_at=now - timedelta(hours=rng.randint(1, 24 * 14)),
                    views=views,
                    likes=int(views * rng.uniform(0.02, 0.18)),
                    comments=int(views * rng.uniform(0.001, 0.02)),
                    shares=int(views * rng.uniform(0.001, 0.03)),
                    author_followers=followers,
                )
            )
        return out

    def fetch_trending(self, platform: str, limit: int = 100) -> list[Video]:
        return self._make(platform, limit, seed=1)

    def fetch_hashtag(self, platform: str, tag: str, limit: int = 100) -> list[Video]:
        return self._make(platform, limit, seed=hash(tag) % 1000, tag=tag)
