#!/usr/bin/env python3
"""Build a source-linked, bounded morning news snapshot. No AI-generated facts."""
import datetime as dt
import email.utils
import html
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

primary_query = os.environ.get("NEWS_QUERY", "artificial intelligence").strip()
queries = []
for candidate in (
    primary_query,
    "artificial intelligence",
    "AI automation work economy",
    "technology policy science",
):
    if candidate and candidate not in queries:
        queries.append(candidate)

items, seen = [], set()
successful_queries = []
for query in queries:
    params = urllib.parse.urlencode({
        "q": query + " when:7d",
        "hl": "en-US",
        "gl": "US",
        "ceid": "US:en",
    })
    url = "https://news.google.com/rss/search?" + params
    request = urllib.request.Request(
        url, headers={"User-Agent": "UselessInstrumentsMorningNews/1.0"}
    )
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            xml = response.read(3_000_000)
        root = ET.fromstring(xml)
    except Exception as exc:
        print(f"Search failed for {query!r}: {exc}")
        continue

    found_for_query = False
    for entry in root.findall("./channel/item"):
        raw_title = html.unescape((entry.findtext("title") or "").strip())
        link = (entry.findtext("link") or "").strip()
        if not raw_title or not link.startswith("https://"):
            continue
        key = (raw_title.lower(), link)
        if key in seen:
            continue
        seen.add(key)
        source = entry.findtext("source") or "Google News"
        date = entry.findtext("pubDate") or ""
        try:
            published = email.utils.parsedate_to_datetime(date).astimezone(
                dt.timezone.utc
            ).isoformat()
        except (TypeError, ValueError, OverflowError):
            published = ""
        items.append({
            "title": raw_title[:240],
            "url": link,
            "source": source[:100],
            "published": published,
        })
        found_for_query = True
        if len(items) >= 18:
            break
    if found_for_query:
        successful_queries.append(query)
    if len(items) >= 18:
        break

if not items:
    raise RuntimeError(
        "No current RSS items returned from primary or fallback queries; "
        "leaving existing news.json unchanged"
    )

payload = {
    "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    "feed": "Google News RSS",
    "queries": successful_queries,
    "items": items,
}
Path("news.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(f"Saved {len(items)} headlines from {len(successful_queries)} query set(s)")
