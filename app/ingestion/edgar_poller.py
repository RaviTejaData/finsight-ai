import os
import requests
import feedparser
from dotenv import load_dotenv

load_dotenv()
HEADERS = {"User-Agent": os.getenv("SEC_USER_AGENT")}
FEED_URL = (
    "https://www.sec.gov/cgi-bin/browse-edgar"
    "?action=getcurrent&type=10-K&count=40&output=atom"
)


def fetch_latest_filings():
    resp = requests.get(FEED_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)
    return [
        {"id": e.id, "title": e.title, "link": e.link, "updated": e.updated}
        for e in feed.entries
    ]


if __name__ == "__main__":
    for f in fetch_latest_filings():
        print(f["updated"], "|", f["title"])
