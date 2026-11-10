import re
import sys
import warnings
from pathlib import Path
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

SEP = r"[^a-z0-9]{0,10}"


def h(num, title):
    return rf"item{SEP}{num}{SEP}{title}"


MARKERS = {
    "business": h("1", "business"),
    "risk_factors": h("1a", r"risk\s*factors"),
    "unresolved": h("1b", "unresolved"),
    "cybersecurity": h("1c", "cybersecurity"),
    "properties": h("2", "properties"),
    "mdna": h("7", r"management.{1,2}s\s*discussion"),
    "market_risk": h("7a", "quantitative"),
    "financials": h("8", r"financial\s*statements"),
    "changes": h("9", "changes"),
}
KEEP = {"business", "risk_factors", "mdna", "market_risk"}


def html_to_text(html):
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style"]):
        t.decompose()
    text = soup.get_text("\n").replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n", text)


def split_sections(text):
    positions = []
    for name, pattern in MARKERS.items():
        matches = list(re.finditer(r"^[^a-z0-9]*" + pattern, text, re.I | re.M))
        if matches:
            positions.append((matches[-1].start(), name))
    positions.sort()
    sections = {}
    for i, (start, name) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        if name in KEEP:
            sections[name] = re.sub(r"\s+", " ", text[start:end]).strip()
    return sections


def parse_file(path):
    html = Path(path).read_text(encoding="utf-8", errors="ignore")
    return split_sections(html_to_text(html))


if __name__ == "__main__":
    for name, body in parse_file(sys.argv[1]).items():
        print(f"{name}: {len(body):,} chars | {body[:100]}...")
