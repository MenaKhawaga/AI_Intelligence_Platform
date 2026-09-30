from __future__ import annotations

import math
import re
from collections import Counter

TOKEN_RE = re.compile(r"[A-Za-z0-9_+#.-]+")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text or "") if len(t) > 1]


def build_index(documents: list[dict]) -> dict:
    docs_tokens = [tokenize(d.get("text", "")) for d in documents]
    df = Counter()
    for tokens in docs_tokens:
        df.update(set(tokens))
    n = max(1, len(documents))
    vocabulary = sorted(df)
    idf = {term: math.log((1 + n) / (1 + df[term])) + 1.0 for term in vocabulary}
    vectors = []
    for tokens in docs_tokens:
        tf = Counter(tokens)
        vec = {term: (1 + math.log(count)) * idf[term] for term, count in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        vectors.append({k: v / norm for k, v in vec.items()})
    return {"documents": documents, "idf": idf, "vectors": vectors}


def embed_query(query: str, idf: dict[str, float]) -> dict[str, float]:
    tf = Counter(tokenize(query))
    vec = {term: (1 + math.log(count)) * idf[term] for term, count in tf.items() if term in idf}
    norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    return {k: v / norm for k, v in vec.items()}


def cosine(query_vector: dict[str, float], document_vector: dict[str, float]) -> float:
    if not query_vector or not document_vector:
        return 0.0
    return sum(v * document_vector.get(k, 0.0) for k, v in query_vector.items())
