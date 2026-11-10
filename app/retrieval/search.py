import os
import sys
import psycopg
from pgvector.psycopg import register_vector
from app.processing.embedder import embed_query

DB_URL = os.getenv(
    "DATABASE_URL", "postgresql://finsight:finsight@localhost:5433/finsight"
)
COLS = ["chunk_id", "accession", "section", "text", "score"]
FILTERS = """
    (%(section)s::text IS NULL OR section = %(section)s)
    AND (%(accession)s::text IS NULL OR accession = %(accession)s)
"""


def _run(sql, params):
    with psycopg.connect(DB_URL) as conn:
        register_vector(conn)
        rows = conn.execute(sql, params).fetchall()
    return [dict(zip(COLS, r)) for r in rows]


def vector_search(query, k=5, section=None, accession=None):
    sql = f"""
        SELECT chunk_id, accession, section, text,
               1 - (embedding <=> %(q)s) AS score
        FROM chunks WHERE {FILTERS}
        ORDER BY embedding <=> %(q)s LIMIT %(k)s
    """
    return _run(sql, {"q": embed_query(query), "section": section,
                      "accession": accession, "k": k})


def keyword_search(query, k=5, section=None, accession=None):
    sql = f"""
        SELECT chunk_id, accession, section, text, ts_rank_cd(tsv, q) AS score
        FROM chunks,
             to_tsquery('english', replace(plainto_tsquery('english', %(query)s)::text, '&', '|')) q
        WHERE tsv @@ q AND {FILTERS}
        ORDER BY score DESC LIMIT %(k)s
    """
    return _run(sql, {"query": query, "section": section,
                      "accession": accession, "k": k})


def hybrid_search(query, k=5, section=None, accession=None, candidates=20, rrf_k=60):
    results = {}
    for source, hits in [("vec", vector_search(query, candidates, section, accession)),
                         ("kw", keyword_search(query, candidates, section, accession))]:
        for rank, hit in enumerate(hits, start=1):
            entry = results.setdefault(hit["chunk_id"], {**hit, "score": 0.0, "sources": []})
            entry["score"] += 1 / (rrf_k + rank)
            entry["sources"].append(f"{source}#{rank}")
    return sorted(results.values(), key=lambda r: r["score"], reverse=True)[:k]


if __name__ == "__main__":
    mode, query = sys.argv[1], sys.argv[2]
    section = sys.argv[3] if len(sys.argv) > 3 else None
    search = {"vector": vector_search, "keyword": keyword_search, "hybrid": hybrid_search}[mode]
    for r in search(query, section=section):
        src = " ".join(r.get("sources", []))
        print(f"{r['score']:.4f} | {r['section']:<12} | {r['accession']} | {src:<14} | {r['text'][:90]}...")
