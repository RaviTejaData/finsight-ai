CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id        TEXT PRIMARY KEY,
    accession       TEXT NOT NULL,
    section         TEXT NOT NULL,
    chunk_index     INT  NOT NULL,
    text            TEXT NOT NULL,
    tokens          INT,
    embedding       vector(384),
    embedding_model TEXT NOT NULL,
    tsv             tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw
    ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chunks_tsv_gin ON chunks USING gin (tsv);
CREATE INDEX IF NOT EXISTS chunks_accession ON chunks (accession);
CREATE INDEX IF NOT EXISTS chunks_section ON chunks (section);
