from collections import defaultdict
from datetime import datetime, timedelta, timezone

from app.models import Video


def engagement_rate(v: Video) -> float:
    """(likes + comments + shares) / views."""
    return (v.likes + v.comments + v.shares) / v.views if v.views else 0.0


def virality_score(v: Video) -> float:
    """Views relative to follower count: high = reached beyond the creator's audience."""
    return v.views / max(v.author_followers, 1)


def top_hashtags(videos: list[Video], n: int = 10) -> list[dict]:
    agg: dict[str, dict] = defaultdict(lambda: {"videos": 0, "views": 0, "eng": 0.0})
    for v in videos:
        for tag in set(v.hashtags):
            a = agg[tag]
            a["videos"] += 1
            a["views"] += v.views
            a["eng"] += engagement_rate(v)
    rows = [
        {"hashtag": t, "videos": a["videos"], "views": a["views"],
         "avg_engagement": round(a["eng"] / a["videos"], 4)}
        for t, a in agg.items()
    ]
    return sorted(rows, key=lambda r: r["views"], reverse=True)[:n]


def rising_hashtags(videos: list[Video], days: int = 3, n: int = 10) -> list[dict]:
    """Hashtags whose share of recent posts beats their share of older posts."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    recent = [v for v in videos if v.posted_at >= cutoff]
    older = [v for v in videos if v.posted_at < cutoff]
    if not recent or not older:
        return []

    def share(vs: list[Video]) -> dict[str, float]:
        c: dict[str, int] = defaultdict(int)
        for v in vs:
            for t in set(v.hashtags):
                c[t] += 1
        return {t: k / len(vs) for t, k in c.items()}

    r, o = share(recent), share(older)
    rows = [{"hashtag": t, "recent_share": round(s, 3), "older_share": round(o.get(t, 0), 3),
             "growth": round(s - o.get(t, 0), 3)} for t, s in r.items()]
    return sorted(rows, key=lambda x: x["growth"], reverse=True)[:n]


def top_sounds(videos: list[Video], n: int = 10) -> list[dict]:
    c: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for v in videos:
        if v.sound:
            c[v.sound][0] += 1
            c[v.sound][1] += v.views
    rows = [{"sound": s, "videos": a, "views": b} for s, (a, b) in c.items()]
    return sorted(rows, key=lambda r: r["videos"], reverse=True)[:n]


def best_posting_hours(videos: list[Video], n: int = 5) -> list[dict]:
    """UTC hours ranked by average engagement rate."""
    h: dict[int, list[float]] = defaultdict(list)
    for v in videos:
        h[v.posted_at.hour].append(engagement_rate(v))
    rows = [{"hour_utc": k, "avg_engagement": round(sum(x) / len(x), 4), "videos": len(x)}
            for k, x in h.items()]
    return sorted(rows, key=lambda r: r["avg_engagement"], reverse=True)[:n]


def breakout_videos(videos: list[Video], n: int = 10) -> list[Video]:
    return sorted(videos, key=virality_score, reverse=True)[:n]
