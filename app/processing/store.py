import os
import sys
import psycopg
from pgvector.psycopg import register_vector
from app.processing.chunker import chunk_filing
from app.processing.embedder import embed_texts, MODEL_NAME

DB_URL = os.getenv(
    "DATABASE_URL", "postgresql://finsight:finsight@localhost:5433/finsight"
)

UPSERT = """
INSERT INTO chunks (chunk_id, accession, section, chunk_index, text, tokens,
                    embedding, embedding_model)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (chunk_id) DO UPDATE SET
    text = EXCLUDED.text,
    tokens = EXCLUDED.tokens,
    embedding = EXCLUDED.embedding,
    embedding_model = EXCLUDED.embedding_model
"""


def store_filing(path):
    chunks = chunk_filing(path)
    if not chunks:
        return 0
    to_embed = [c["section"].replace("_", " ") + ": " + c["text"] for c in chunks]
    vectors = embed_texts(to_embed)
    rows = [
        (c["chunk_id"], c["accession"], c["section"], c["chunk_index"],
         c["text"], c["tokens"], v, MODEL_NAME)
        for c, v in zip(chunks, vectors)
    ]
    with psycopg.connect(DB_URL) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.executemany(UPSERT, rows)
    return len(rows)


if __name__ == "__main__":
    for path in sys.argv[1:]:
        print(f"{store_filing(path):>5} chunks  {path}")
