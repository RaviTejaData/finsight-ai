import os
import sys
import psycopg
from pgvector.psycopg import register_vector
from app.processing.embedder import embed_query

DB_URL = os.getenv(
    "DATABASE_URL", "postgresql://finsight:finsight@localhost:5433/finsight"
)


def vector_search(query, k=5, section=None, accession=None):
    sql = """
        SELECT chunk_id, accession, section, text,
               1 - (embedding <=> %(q)s) AS score
        FROM chunks
        WHERE (%(section)s::text IS NULL OR section = %(section)s)
          AND (%(accession)s::text IS NULL OR accession = %(accession)s)
        ORDER BY embedding <=> %(q)s
        LIMIT %(k)s
    """
    params = {"q": embed_query(query), "section": section,
              "accession": accession, "k": k}
    with psycopg.connect(DB_URL) as conn:
        register_vector(conn)
        rows = conn.execute(sql, params).fetchall()
    cols = ["chunk_id", "accession", "section", "text", "score"]
    return [dict(zip(cols, r)) for r in rows]


if __name__ == "__main__":
    query = sys.argv[1]
    section = sys.argv[2] if len(sys.argv) > 2 else None
    for r in vector_search(query, section=section):
        print(f"{r['score']:.3f} | {r['section']:<12} | {r['accession']} | {r['text'][:110]}...")
