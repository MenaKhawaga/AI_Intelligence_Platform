from __future__ import annotations


def rerank(results: list[dict], query: str, limit: int = 8) -> list[dict]:
    terms = {x.lower() for x in query.split() if x.strip()}
    for item in results:
        title_terms = set(item.get("title", "").lower().split())
        item["score"] = round(float(item.get("score", 0)) + 0.08 * len(terms & title_terms), 4)
    return sorted(results, key=lambda x: x["score"], reverse=True)[:limit]
