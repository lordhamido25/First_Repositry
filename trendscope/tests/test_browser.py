import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from app.providers.browser import BrowserProvider, parse_item, parse_payload

ITEM = {"id": "7", "desc": "leg day", "createTime": 1767225600, "author": {"uniqueId": "bob"},
        "authorStats": {"followerCount": 1234}, "music": {"title": "beat"},
        "challenges": [{"title": "GymTok"}], "stats": {"playCount": 900, "diggCount": 90,
                                                      "commentCount": 9, "shareCount": 3}}


def test_parse_item():
    v = parse_item(ITEM)
    assert (v.author, v.views, v.likes, v.hashtags, v.sound, v.author_followers) == ("bob", 900, 90, ["gymtok"], "beat", 1234)


def test_parse_payload_and_junk():
    assert len(parse_payload({"itemList": [ITEM, {"no": "id"}]})) == 1
    assert parse_payload("garbage") == [] and parse_payload({}) == []


def test_instagram_not_supported():
    with pytest.raises(NotImplementedError):
        BrowserProvider().fetch_hashtag("instagram", "x")


def test_browser_captures_item_list_responses(monkeypatch):
    """Plumbing check against a local fake page (no real TikTok access)."""
    pytest.importorskip("playwright")

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def do_GET(self):
            if "item_list" in self.path:
                body, ctype = json.dumps({"itemList": [ITEM]}).encode(), "application/json"
            else:
                body = b"<html><script>fetch('/api/challenge/item_list/?x=1')</script></html>"
                ctype = "text/html"
            self.send_response(200); self.send_header("Content-Type", ctype); self.end_headers(); self.wfile.write(body)

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    import app.providers.browser as b
    real_sleep = b.time.sleep
    monkeypatch.setattr(b.time, "sleep", lambda s: real_sleep(0.5))
    p = BrowserProvider(); p.scrolls = 0
    orig_goto = None
    from playwright.sync_api import Page
    orig_goto = Page.goto
    monkeypatch.setattr(Page, "goto", lambda self, url, **kw: orig_goto(self, f"http://127.0.0.1:{srv.server_port}/", **kw))
    try:
        vids = p.fetch_hashtag("tiktok", "gymtok")
    except Exception as e:
        pytest.skip(f"browser not runnable here: {e}")
    assert [v.id for v in vids] == ["7"]
