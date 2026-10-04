# TrendScope

Trend analytics for TikTok and Instagram Reels: top and rising hashtags, trending sounds,
best posting hours, and breakout videos (views far above the creator's follower count).

## Run it

```bash
cd trendscope
pip install -r requirements.txt
python -m pytest                       # tests
uvicorn app.main:app --reload          # http://127.0.0.1:8000/docs
```

```bash
curl -X POST "localhost:8000/refresh/tiktok?limit=200"   # fetch + store
curl localhost:8000/trends/tiktok                         # analytics
```

Open http://127.0.0.1:8000/ for the dashboard. It runs on fake data until you set up Apify:

```bash
export TRENDSCOPE_PROVIDER=apify
export APIFY_TOKEN=...                      # Apify console -> Settings -> Integrations
export TRENDSCOPE_SEED_TAGS=fitness,gymtok  # the niche(s) you want to track
uvicorn app.main:app
```

Click **Refresh data**. Each refresh runs Apify actors and costs Apify credits, so keep
`limit` small while testing. Actors used: `clockworks/tiktok-scraper` and
`apify/instagram-hashtag-scraper` (change them with `APIFY_*_ACTOR`). The Apify adapter
is tested against sample payloads only, not live Apify, so check one real refresh and
adjust `app/providers/apify.py` if an actor's output differs.

## Trend history and auto-refresh

Every refresh stores a snapshot of each video's views/likes/comments. With 2+ refreshes at
different times the dashboard shows **fastest growing videos** and **hashtag momentum**
(views gained over the last 48h). To refresh automatically while the server runs:

```powershell
$env:TRENDSCOPE_REFRESH_HOURS="6"     # every 6 hours; unset or 0 = off
$env:TRENDSCOPE_REFRESH_LIMIT="100"   # videos per platform per run (each run costs Apify credit)
```

The server must stay running for this to work. A hosted deployment keeps it running.

## DIY browser provider (personal/learning use, TikTok only)

Reads public TikTok hashtag pages with a headless browser and captures the page's own video-list
responses. No Apify needed, no logins, no proxies. It stops and reports if TikTok shows a
CAPTCHA/login wall instead of working around it.

```powershell
pip install -r requirements-browser.txt
python -m playwright install chromium
$env:TRENDSCOPE_PROVIDER="browser"
$env:TRENDSCOPE_SEED_TAGS="fitness"      # keep this list short
$env:TRENDSCOPE_HEADLESS="0"             # optional: watch the browser window
python -m uvicorn app.main:app --reload
```

Then pick TikTok and click Refresh data (takes ~30s per hashtag). Not tested against live
TikTok: if it returns nothing or odd numbers, edit `parse_item()` in `app/providers/browser.py`.
Instagram is not supported here. Keep volumes small and don't run it on a tight schedule.

## Data sources (the important decision)

Scraping TikTok or Instagram directly violates their terms of service and breaks often,
especially on Instagram. A paying product shouldn't depend on it. Options, safest first:

1. **Official APIs**: TikTok Research API (restricted access), Instagram Graph API
   (only your own or connected business accounts).
2. **Licensed data providers** that handle proxies and breakage for you, such as Apify,
   Bright Data, EnsembleData, ScrapeCreators or HasData. You pay per request and
   map their output into `app/models.py::Video`.
3. **DIY scraping**: cheapest, but expect blocks and legal risk. Avoid it at scale.

To add one, subclass `app/providers/base.py::Provider` and register it in
`app/providers/__init__.py`. Nothing else changes.

## Making it profitable

- **Who pays**: social media managers, agencies, creators, e-commerce brands, and marketers
  who need to know what to post this week. Sell outcomes ("3 trends to post this week"),
  not raw data.
- **Pricing**: free tier (limited trends, delayed data), Pro $19-49/mo (full dashboard,
  alerts, niche filters), Agency $99-299/mo (multi-niche, exports, API, white-label reports).
- **Hooks that retain**: weekly email digest per niche, alerts when a hashtag or sound
  starts rising, "what to post today" suggestions (LLM-written from the analytics).
- **Cost control**: data API calls are your main cost. Cache and refresh on a schedule
  (e.g. every few hours) instead of fetching per user request.
- **Minimum to launch**: pick one niche, real provider, a simple frontend,
  Stripe subscriptions, auth, and a daily refresh job. Get 10 paying users before building more.

## Roadmap

1. ~~Apify adapter~~ done (needs a live check)
2. Frontend dashboard (Next.js or plain HTML + charts)
3. Auth + Stripe billing
4. Scheduled refresh + trend history (snapshots to compute true velocity)
5. Alerts and weekly digests
