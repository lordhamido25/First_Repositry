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

It runs on fake data (`MockProvider`) until you add a real provider.

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

1. Real provider adapter (start with one, e.g. Apify)
2. Frontend dashboard (Next.js or plain HTML + charts)
3. Auth + Stripe billing
4. Scheduled refresh + trend history (snapshots to compute true velocity)
5. Alerts and weekly digests
