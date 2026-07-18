"""
Fetches upcoming Tokyo tech events from Connpass (and, if a token is set,
Doorkeeper) and writes a single normalized JSON file that the static
front-end reads: public/events.json

Run manually:
    CONNPASS_KEY=xxx python scripts/fetch_events.py

Run on a schedule via GitHub Actions (see .github/workflows/fetch_events.yml).
"""

import json
import os
import sys
from datetime import datetime, timezone

import requests

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "public", "events.json")

CONNPASS_KEY = os.environ.get("CONNPASS_KEY")  # optional, raises your rate limit
DOORKEEPER_TOKEN = os.environ.get("DOORKEEPER_TOKEN")  # optional, enables Doorkeeper

# Keywords to sweep across Connpass so we catch more than one niche.
# Feel free to edit this list.
CONNPASS_KEYWORDS = ["エンジニア", "AI", "Python", "Networking", "スタートアップ", "ネットワーク", "AWS", "Foreign Engineers", "python","ai"]


def fetch_connpass_events():
    """Query Connpass for events, filter to Tokyo, normalize the shape."""
    url = "https://connpass.com/api/v1/event/"
    headers = {"User-Agent": "TokyoTechBoard/1.0"}
    if CONNPASS_KEY:
        headers["X-Connpass-Token"] = CONNPASS_KEY

    seen_ids = set()
    results = []

    for keyword in CONNPASS_KEYWORDS:
        params = {"keyword": keyword, "count": 30, "order": 2}
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"[connpass] failed for keyword={keyword!r}: {exc}", file=sys.stderr)
            continue

        for item in resp.json().get("events", []):
            event_id = item.get("event_id")
            if event_id in seen_ids:
                continue

            address = item.get("address") or ""
            place = item.get("place") or ""
            is_online = "オンライン" in place or "online" in place.lower()
            is_tokyo = "東京" in address or "Tokyo" in address or is_online

            if not is_tokyo:
                continue

            seen_ids.add(event_id)
            results.append(
                {
                    "source": "connpass",
                    "id": f"connpass-{event_id}",
                    "title": item.get("title"),
                    "url": item.get("event_url"),
                    "start": item.get("started_at"),
                    "end": item.get("ended_at"),
                    "venue": "Online" if is_online else (place or "TBA"),
                    "address": address,
                    "group": (item.get("series") or {}).get("title"),
                    "fee": "Free",  # Connpass events are overwhelmingly free
                    "capacity": item.get("limit"),
                    "accepted": item.get("accepted"),
                    "description": (item.get("catch") or "").strip(),
                }
            )

    return results


def fetch_doorkeeper_events():
    """Query Doorkeeper for Tokyo events. Skipped if no token is configured."""
    if not DOORKEEPER_TOKEN:
        return []

    url = "https://api.doorkeeper.jp/events"
    headers = {"Authorization": f"Bearer {DOORKEEPER_TOKEN}"}
    params = {"locale": "en", "prefecture": "tokyo", "sort": "starts_at"}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[doorkeeper] failed: {exc}", file=sys.stderr)
        return []

    results = []
    for wrapper in resp.json():
        item = wrapper.get("event", wrapper)
        results.append(
            {
                "source": "doorkeeper",
                "id": f"doorkeeper-{item.get('id')}",
                "title": item.get("title"),
                "url": item.get("public_url"),
                "start": item.get("starts_at"),
                "end": item.get("ends_at"),
                "venue": (item.get("venue") or {}).get("name") or "TBA",
                "address": (item.get("venue") or {}).get("address") or "",
                "group": (item.get("group") or {}).get("name"),
                "fee": "Free" if not item.get("ticket") else "Paid",
                "capacity": item.get("participants_limit"),
                "accepted": item.get("participants_count"),
                "description": (item.get("description") or "")[:200],
            }
        )
    return results


def is_upcoming(event):
    if not event.get("start"):
        return False
    try:
        start = datetime.fromisoformat(event["start"])
    except ValueError:
        return False
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    return start >= datetime.now(timezone.utc)


def main():
    events = fetch_connpass_events() + fetch_doorkeeper_events()
    events = [e for e in events if is_upcoming(e)]
    events.sort(key=lambda e: e["start"])

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(events),
        "events": events,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(events)} events to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
