import os
import re
import json
import time
import hashlib
import numpy as np
import redis
from redis.commands.search.field import TextField, VectorField
from redis.commands.search.query import Query
from app.processing.embedder import embed_query, DIM

try:
    from redis.commands.search.index_definition import IndexDefinition, IndexType
except ImportError:
    from redis.commands.search.indexDefinition import IndexDefinition, IndexType

INDEX = "idx:llm_cache"
PREFIX = "llmcache:"
THRESHOLD = float(os.getenv("CACHE_DISTANCE_THRESHOLD", "0.20"))
TTL_SECONDS = 24 * 3600
KEY_RE = re.compile(r"\b(?:\d{1,2}-[a-z]|[a-z]-\d{1,2}|(?:19|20)\d{2}|q[1-4])\b", re.I)
r = redis.Redis(host="localhost", port=6379)


def _ensure_index():
    try:
        r.ft(INDEX).info()
    except redis.ResponseError:
        r.ft(INDEX).create_index(
            [TextField("question"),
             VectorField("embedding", "HNSW", {
                 "TYPE": "FLOAT32", "DIM": DIM, "DISTANCE_METRIC": "COSINE"})],
            definition=IndexDefinition(prefix=[PREFIX], index_type=IndexType.HASH),
        )


def _vec(text):
    return embed_query(text).astype(np.float32).tobytes()


def _key_terms(text):
    return {t.lower() for t in KEY_RE.findall(text)}


def lookup(question):
    _ensure_index()
    q = (Query("*=>[KNN 1 @embedding $vec AS dist]")
         .sort_by("dist").return_fields("question", "answer", "dist").dialect(2))
    res = r.ft(INDEX).search(q, query_params={"vec": _vec(question)})
    if not res.docs:
        return None
    d = res.docs[0]
    close_enough = float(d.dist) <= THRESHOLD
    same_terms = _key_terms(d.question) == _key_terms(question)
    if close_enough and same_terms:
        return {"answer": json.loads(d.answer), "cached_question": d.question,
                "distance": float(d.dist)}
    return None


def store(question, answer):
    _ensure_index()
    key = PREFIX + hashlib.sha256(question.lower().encode()).hexdigest()[:16]
    r.hset(key, mapping={"question": question, "answer": json.dumps(answer),
                         "embedding": _vec(question), "created": time.time()})
    r.expire(key, TTL_SECONDS)


if __name__ == "__main__":
    from app.gateway.llm import chat
    seed = "What is a 10-K filing?"
    if not lookup(seed):
        store(seed, chat([{"role": "user", "content": seed}])["content"])
        print("MISS -> called LLM and stored")
    for q in ["What is a 10-K filing?",
              "Can you explain what a 10-K report is?",
              "What does a 10-K filing mean?",
              "What is a 10-Q filing?",
              "What is an 8-K filing?",
              "What was Emerson's revenue last year?"]:
        hit = lookup(q)
        info = f"dist={hit['distance']:.3f} (matched: {hit['cached_question']})" if hit else ""
        print(f"{'HIT ' if hit else 'MISS'} | {q:<42} | {info}")
