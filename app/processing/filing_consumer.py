import os
import re
import json
import time
import requests
from confluent_kafka import Consumer
from dotenv import load_dotenv
from app.processing.store import store_filing

load_dotenv()
HEADERS = {"User-Agent": os.getenv("SEC_USER_AGENT")}
TOPIC = "filings.new"
RAW_DIR = "data/raw"
ACC_RE = re.compile(r"(\d{10}-\d{2}-\d{6})")

consumer = Consumer({
    "bootstrap.servers": "localhost:19092",
    "group.id": "filing-processor",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,
})


def primary_doc_url(cik, accession):
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    recent = requests.get(url, headers=HEADERS, timeout=30).json()["filings"]["recent"]
    for acc, doc in zip(recent["accessionNumber"], recent["primaryDocument"]):
        if acc == accession:
            folder = accession.replace("-", "")
            return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{folder}/{doc}"
    return None


def download(filing, accession, path):
    doc_url = primary_doc_url(filing["cik"], accession)
    if not doc_url:
        return False
    html = requests.get(doc_url, headers=HEADERS, timeout=60).text
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    time.sleep(0.2)
    return True


def process(filing):
    m = ACC_RE.search(filing["link"])
    if not m or filing["cik"] == "unknown":
        return
    accession = m.group(1)
    path = f"{RAW_DIR}/{accession}.htm"
    if not os.path.exists(path) and not download(filing, accession, path):
        print("Not found yet:", accession)
        return
    t = time.time()
    n = store_filing(path)
    print(f"Indexed {n:>4} chunks in {time.time() - t:5.1f}s | {filing['title'][:60]}")


if __name__ == "__main__":
    os.makedirs(RAW_DIR, exist_ok=True)
    consumer.subscribe([TOPIC])
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None or msg.error():
                continue
            filing = json.loads(msg.value())
            if "link" in filing:
                process(filing)
            consumer.commit(msg)
    finally:
        consumer.close()
