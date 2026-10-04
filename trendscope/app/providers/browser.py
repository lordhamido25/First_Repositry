"""DIY provider: reads public TikTok hashtag pages with a headless browser.

How it works: open https://www.tiktok.com/tag/<tag> like a normal visitor, listen to the
page's own background requests, and keep the JSON responses that carry the video list
(URLs containing "item_list"). No logins, no proxies, no CAPTCHA solving.

Be a polite visitor: one page at a time, pauses between actions, small volumes. If TikTok
shows a CAPTCHA or login wall, this provider stops and says so instead of working around it.

Personal/educational use. Scraping may violate TikTok's terms of service.
Field names below are from observed TikTok responses and may change without notice;
if results come back empty or odd, fix parse_item().
"""
import json
import os
import random
import time
from datetime import datetime, timezone
from typing import Any

from app.models import Video
from app.providers.apify import _dt, _int  # shared tolerant converters
from app.providers.base import Provider


def parse_item(item: dict) -> Video | None:
    if not item.get("id"):
        return None
    author = item.get("author")
    author_stats = item.get("authorStats") or item.get("authorStatsV2") or {}
    if isinstance(author, dict):
        name = author.get("uniqueId") or author.get("nickname") or "unknown"
    else:
        name = author or "unknown"
    stats = item.get("stats") or item.get("statsV2") or {}
    tags = [str(c["title"]).lower() for c in item.get("challenges") or [] if c.get("title")]
    if not tags:
        tags = [str(t["hashtagName"]).lower() for t in item.get("textExtra") or [] if t.get("hashtagName")]
    music = item.get("music") or {}
    return Video(
        id=str(item["id"]),
        platform="tiktok",
        author=str(name),
        caption=item.get("desc") or "",
        hashtags=tags,
        sound=music.get("title"),
        posted_at=_dt(item.get("createTime")),
        views=_int(stats.get("playCount")),
        likes=_int(stats.get("diggCount")),
        comments=_int(stats.get("commentCount")),
        shares=_int(stats.get("shareCount")),
        author_followers=_int(author_stats.get("followerCount")),
    )


def parse_payload(body: Any) -> list[Video]:
    """Pull videos out of one captured JSON response."""
    items = body.get("itemList") or body.get("item_list") or [] if isinstance(body, dict) else []
    return [v for v in (parse_item(i) for i in items if isinstance(i, dict)) if v]


class BrowserProvider(Provider):
    name = "browser"

    def __init__(self):
        self.seeds = [s.strip().lstrip("#") for s in os.getenv("TRENDSCOPE_SEED_TAGS", "fyp").split(",") if s.strip()]
        self.headless = os.getenv("TRENDSCOPE_HEADLESS", "1") != "0"
        self.scrolls = int(os.getenv("TRENDSCOPE_SCROLLS", "4"))

    def fetch_hashtag(self, platform: str, tag: str, limit: int = 100) -> list[Video]:
        if platform != "tiktok":
            raise NotImplementedError(
                "The browser provider supports TikTok only. Instagram needs a login for most "
                "content, which risks your account; use the Apify provider for Instagram."
            )
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError("Install Playwright: pip install playwright && python -m playwright install chromium")

        found: dict[str, Video] = {}

        def on_response(resp):
            if "item_list" not in resp.url:
                return
            try:
                for v in parse_payload(json.loads(resp.body())):
                    found[v.id] = v
            except Exception:
                pass  # non-JSON or empty body; ignore

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=self.headless, executable_path=os.getenv("TRENDSCOPE_CHROMIUM") or None)
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                page.on("response", on_response)
                page.goto(f"https://www.tiktok.com/tag/{tag.lstrip('#')}", wait_until="domcontentloaded", timeout=60000)
                time.sleep(random.uniform(3, 5))
                for _ in range(self.scrolls):
                    if len(found) >= limit:
                        break
                    page.mouse.wheel(0, 2500)
                    time.sleep(random.uniform(2, 4))
                blocked = page.locator("text=/verify|captcha|log in to/i").count() > 0
            finally:
                browser.close()

        if not found:
            hint = "TikTok showed a verification/login wall" if blocked else "no video data was captured"
            raise RuntimeError(f"{hint} for #{tag}. Try again later, set TRENDSCOPE_HEADLESS=0 to watch the browser, or use Apify.")
        return list(found.values())[:limit]

    def fetch_trending(self, platform: str, limit: int = 100) -> list[Video]:
        per_tag = max(limit // max(len(self.seeds), 1), 1)
        seen: dict[str, Video] = {}
        for i, tag in enumerate(self.seeds):
            if i:
                time.sleep(random.uniform(5, 10))  # be gentle between pages
            for v in self.fetch_hashtag(platform, tag, per_tag):
                seen[v.id] = v
        return list(seen.values())
