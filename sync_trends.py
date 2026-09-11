#!/usr/bin/env python3
"""
Salem Rate Card - Seasonal Purchasing Trends Sync
====================================================
Pulls US seasonal search-interest patterns by advertiser category from
Google Trends and writes trends_data.json for the Seasonal Trends page
(trends.html). Intended to run nightly via GitHub Actions, the same way
sync_rates.py keeps the rate tables current from Google Sheets.

Method
------
For each category we query a representative head-term keyword scoped to
that category's Google Trends category ID, over a 5-year US lookback.
Five years (rather than the last 12 months) smooths one-off news spikes
and gives a stable read on WHEN each category historically peaks. Values
are then averaged by calendar month and normalized 0-100 *within each
category* (its own peak month = 100), because raw search volume differs
enormously between categories (e.g. "Shopping" vs. "Pets & Animals") --
normalizing per category is what makes the seasonal SHAPE comparable
across a heatmap, which is the point of this chart. Absolute cross-
category volume is not comparable in this view.

Resilience
----------
Google Trends' unofficial API (via pytrends) is well known to throttle
or block requests from shared/CI IP ranges, including GitHub Actions
runners. This script treats that as an expected failure mode, not a
crash: each category is fetched independently, paused between requests
to stay clear of the informal rate limit, and on failure we keep that
category's last-known-good values (flagged "stale") rather than
blanking the chart or leaving broken data. The page always shows
`updated_at` and per-category source/staleness so nothing is presented
as fresher than it is.

Sheet-free by design: unlike sync_rates.py, there's no Google Sheet of
"seasonal trends" to sync from -- Google Trends itself is the source.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

OUTPUT_FILE = "trends_data.json"
GEO = "US"
TIMEFRAME = "today 5-y"
REQUEST_PAUSE_SECONDS = 65  # stay well clear of Google Trends' informal rate limit

# Google Trends top-level category IDs (Google Ads/Trends taxonomy) paired with
# one representative head-term keyword. Querying a keyword scoped to the
# category (rather than the category filter with no keyword) is the reliable
# way to pull a consistent interest-over-time series through pytrends.
CATEGORIES = [
    {"name": "Retail & Shopping",       "cat": 18,  "kw": "black friday deals"},
    {"name": "Automotive",              "cat": 47,  "kw": "car deals"},
    {"name": "Travel & Hospitality",    "cat": 67,  "kw": "flight deals"},
    {"name": "Finance & Insurance",     "cat": 7,   "kw": "tax refund"},
    {"name": "Home & Garden",           "cat": 11,  "kw": "home improvement"},
    {"name": "Health",                  "cat": 45,  "kw": "gym membership"},
    {"name": "Beauty & Fitness",        "cat": 44,  "kw": "skincare routine"},
    {"name": "Computers & Electronics", "cat": 5,   "kw": "laptop deals"},
    {"name": "Internet & Telecom",      "cat": 13,  "kw": "new phone deals"},
    {"name": "Food & Drink",            "cat": 71,  "kw": "restaurant reservations"},
    {"name": "Real Estate",             "cat": 29,  "kw": "homes for sale"},
    {"name": "Jobs & Education",        "cat": 958, "kw": "job search"},
    {"name": "Sports",                  "cat": 20,  "kw": "season tickets"},
    {"name": "Games",                   "cat": 8,   "kw": "video game deals"},
    {"name": "Pets & Animals",          "cat": 66,  "kw": "pet supplies"},
    {"name": "Hobbies & Leisure",       "cat": 65,  "kw": "camping gear"},
    {"name": "Arts & Entertainment",    "cat": 3,   "kw": "concert tickets"},
    {"name": "Business & Industrial",   "cat": 12,  "kw": "b2b services"},
]

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fetch_category_seasonality(pytrends, cat_def):
    """Pull a 5-year US series and average it into a 12-point monthly seasonality index."""
    pytrends.build_payload([cat_def["kw"]], cat=cat_def["cat"], timeframe=TIMEFRAME, geo=GEO)
    df = pytrends.interest_over_time()
    if df is None or df.empty:
        raise RuntimeError("empty response from Google Trends")

    monthly_avg = df.groupby(df.index.month)[cat_def["kw"]].mean()
    lo, hi = monthly_avg.min(), monthly_avg.max()
    span = (hi - lo) or 1
    values = [round(((monthly_avg.get(m, lo) - lo) / span) * 100, 1) for m in range(1, 13)]
    return values


def load_existing():
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def main():
    try:
        from pytrends.request import TrendReq
    except ImportError:
        print("pytrends is not installed. `pip install pytrends` and re-run.")
        sys.exit(1)

    pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25))

    existing = load_existing()
    existing_by_name = {c["name"]: c for c in (existing or {}).get("categories", [])}

    results = []
    failures = []
    for i, cat_def in enumerate(CATEGORIES):
        print(f"[{i + 1}/{len(CATEGORIES)}] {cat_def['name']} ...", flush=True)
        try:
            values = fetch_category_seasonality(pytrends, cat_def)
            results.append({"name": cat_def["name"], "values": values, "source": "live"})
            print("  ok")
        except Exception as e:
            print(f"  FAILED: {e}")
            failures.append(cat_def["name"])
            prev = existing_by_name.get(cat_def["name"])
            if prev:
                stale = dict(prev)
                stale["source"] = "stale"
                results.append(stale)
                print("  kept last-known-good values")
            else:
                print("  no prior data to fall back on -- category will be missing this run")

        if i < len(CATEGORIES) - 1:
            time.sleep(REQUEST_PAUSE_SECONDS)

    if not results:
        print("No categories synced and no prior data exists -- leaving nothing to write.")
        sys.exit(1)

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "geo": GEO,
        "timeframe": TIMEFRAME,
        "months": MONTHS,
        "categories": results,
        "failed_categories": failures,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {OUTPUT_FILE}: {len(results)} categories ({len(failures)} failed/stale this run)")


if __name__ == "__main__":
    main()
