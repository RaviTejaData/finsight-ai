import re
import sys
from pathlib import Path
import tiktoken
from app.processing.parser import parse_file

ENC = tiktoken.get_encoding("cl100k_base")
MAX_TOKENS = 400
OVERLAP_TOKENS = 60
SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def n_tokens(text):
    return len(ENC.encode(text))


def split_long(s):
    ids = ENC.encode(s)
    return [ENC.decode(ids[i:i + MAX_TOKENS]) for i in range(0, len(ids), MAX_TOKENS)]


def chunk_section(text):
    sentences = []
    for s in SENT_RE.split(text):
        sentences.extend(split_long(s) if n_tokens(s) > MAX_TOKENS else [s])
    chunks, current, current_tokens = [], [], 0
    for s in sentences:
        t = n_tokens(s)
        if current and current_tokens + t > MAX_TOKENS:
            chunks.append(" ".join(current))
            overlap, ov = [], 0
            for prev in reversed(current):
                ov += n_tokens(prev)
                if ov > OVERLAP_TOKENS:
                    break
                overlap.insert(0, prev)
            current, current_tokens = overlap, sum(n_tokens(x) for x in overlap)
        current.append(s)
        current_tokens += t
    if current:
        chunks.append(" ".join(current))
    return chunks


def chunk_filing(path):
    accession = Path(path).stem
    out = []
    for section, body in parse_file(path).items():
        for i, text in enumerate(chunk_section(body)):
            out.append({
                "chunk_id": f"{accession}:{section}:{i}",
                "accession": accession,
                "section": section,
                "chunk_index": i,
                "text": text,
                "tokens": n_tokens(text),
            })
    return out


if __name__ == "__main__":
    chunks = chunk_filing(sys.argv[1])
    sizes = [c["tokens"] for c in chunks]
    print(f"{len(chunks)} chunks | avg {sum(sizes)//len(sizes)} | max {max(sizes)} tokens")
    print("--- end of chunk 0:", chunks[0]["text"][-150:])
    print("--- start of chunk 1:", chunks[1]["text"][:150])
