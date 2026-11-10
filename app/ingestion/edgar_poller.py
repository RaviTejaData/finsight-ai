import os
import re
import json
import time
import requests
import feedparser
import redis
from confluent_kafka import Producer
from dotenv import load_dotenv

load_dotenv()
HEADERS = {"User-Agent": os.getenv("SEC_USER_AGENT")}
FEED_URL = (
    "https://www.sec.gov/cgi-bin/browse-edgar"
    "?action=getcurrent&type=10-K&count=40&output=atom"
)
TOPIC = "filings.new"
POLL_SECONDS = 60
CIK_RE = re.compile(r"\((\d{10})\)")

producer = Producer({"bootstrap.servers": "localhost:19092"})
r = redis.Redis(host="localhost", port=6379, decode_responses=True)


def fetch_latest_filings():
    resp = requests.get(FEED_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)
    filings = []
    for e in feed.entries:
        m = CIK_RE.search(e.title)
        filings.append({
            "id": e.id,
            "title": e.title,
            "form": e.title.split(" - ")[0],
            "cik": m.group(1) if m else "unknown",
            "link": e.link,
            "updated": e.updated,
        })
    return filings


def publish_new(filings):
    new = [f for f in filings if not r.sismember("edgar:seen", f["id"])]
    for f in new:
        producer.produce(TOPIC, key=f["cik"], value=json.dumps(f))
    producer.flush()
    if new:
        r.sadd("edgar:seen", *[f["id"] for f in new])
    return len(new)


if __name__ == "__main__":
    while True:
        try:
            n = publish_new(fetch_latest_filings())
            print(f"Published {n} new filings")
        except Exception as e:
            print("Error:", e)
        time.sleep(POLL_SECONDS)
