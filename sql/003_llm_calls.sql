CREATE TABLE IF NOT EXISTS llm_calls (
    id            BIGSERIAL PRIMARY KEY,
    created_at    TIMESTAMPTZ DEFAULT now(),
    provider      TEXT,
    model         TEXT,
    input_tokens  INT,
    output_tokens INT,
    cost_usd      NUMERIC(12, 6),
    latency_s     REAL,
    success       BOOLEAN,
    error         TEXT
);
