import httpx

from app.providers.apify import ApifyProvider, parse_instagram, parse_tiktok

TT = {"id": "1", "text": "hi #fyp", "createTimeISO": "2026-01-02T03:04:05.000Z",
      "authorMeta": {"name": "bob", "fans": 1000}, "musicMeta": {"musicName": "song"},
      "diggCount": 50, "playCount": 1000, "commentCount": 5, "shareCount": 2,
      "hashtags": [{"name": "fyp"}, {"name": "Dance"}]}
IG = {"id": "9", "caption": "look #Travel #fyp", "ownerUsername": "amy", "timestamp": "2026-01-02T03:04:05.000Z",
      "videoPlayCount": 500, "likesCount": 40, "commentsCount": 3}


def test_parse_tiktok():
    v = parse_tiktok(TT)
    assert (v.views, v.likes, v.author, v.author_followers, v.sound) == (1000, 50, "bob", 1000, "song")
    assert v.hashtags == ["fyp", "dance"]


def test_parse_instagram_falls_back_to_caption_tags():
    v = parse_instagram(IG)
    assert v.hashtags == ["travel", "fyp"] and v.views == 500


def test_provider_calls_apify_and_dedupes():
    calls = []

    def handler(req: httpx.Request):
        calls.append(req)
        assert req.headers["authorization"] == "Bearer tok"
        return httpx.Response(200, json=[TT])

    p = ApifyProvider("tok", httpx.Client(transport=httpx.MockTransport(handler)))
    p.seeds = ["a", "b"]
    vids = p.fetch_trending("tiktok", 10)
    assert len(calls) == 2 and len(vids) == 1
    assert "clockworks~tiktok-scraper/run-sync-get-dataset-items" in str(calls[0].url)
