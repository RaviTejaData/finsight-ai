from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-small-en-v1.5"
DIM = 384
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
_model = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_texts(texts, batch_size=32):
    return get_model().encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=len(texts) > 100,
    )


def embed_query(query):
    return embed_texts([QUERY_PREFIX + query])[0]


if __name__ == "__main__":
    docs = [
        "The company faces supply chain disruption risks.",
        "Revenue increased 12% due to strong demand.",
        "Our headquarters is located in St. Louis, Missouri.",
    ]
    doc_vecs = embed_texts(docs)
    q = embed_query("What risks does the company face?")
    for d, v in zip(docs, doc_vecs):
        print(f"{float(q @ v):.3f}  {d}")
    print("dim:", doc_vecs.shape[1])
