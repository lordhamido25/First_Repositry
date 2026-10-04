import os

os.environ["TRENDSCOPE_DB"] = ":memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app import analytics  # noqa: E402
from app.main import app  # noqa: E402
from app.providers.mock import MockProvider  # noqa: E402

client = TestClient(app)


def test_analytics_on_mock_data():
    vids = MockProvider().fetch_trending("tiktok", 200)
    assert len(analytics.top_hashtags(vids)) == 10
    assert analytics.top_hashtags(vids)[0]["views"] >= analytics.top_hashtags(vids)[1]["views"]
    assert analytics.rising_hashtags(vids)
    assert analytics.best_posting_hours(vids)
    assert all(0 <= analytics.engagement_rate(v) <= 1 for v in vids)


def test_refresh_then_trends():
    assert client.post("/refresh/tiktok?limit=50").json()["saved"] == 50
    body = client.get("/trends/tiktok").json()
    assert body["videos_analyzed"] == 50
    assert body["top_hashtags"]
    assert client.get("/trends/instagram").json()["videos_analyzed"] == 0


def test_bad_platform():
    assert client.get("/trends/youtube").status_code == 400


def test_growth_from_snapshots():
    from datetime import datetime, timedelta, timezone

    from app.storage import Store

    s = Store(":memory:")
    now = datetime.now(timezone.utc)
    v = MockProvider().fetch_trending("tiktok", 3)
    s.save(v, now - timedelta(hours=10))
    for x in v:
        x.views += 1000
    s.save(v, now)
    g = s.growth("tiktok")
    assert len(g) == 3 and all(r["gain"] == 1000 and r["views_per_hour"] == 100 for r in g)
    assert s.snapshot_count("tiktok") == 2
    assert analytics.fastest_growing(v, g)[0]["gain"] == 1000
    assert analytics.hashtag_momentum(v, g)


def test_single_snapshot_has_no_growth():
    from app.storage import Store

    s = Store(":memory:")
    s.save(MockProvider().fetch_trending("tiktok", 3))
    assert s.growth("tiktok") == []
