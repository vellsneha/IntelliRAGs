"""
Retrieval metrics: Hit@1, Recall@k, MRR.

Each function takes:
- retrieved_ids: ordered list of chunk IDs returned by the retriever (best first)
- gold_ids: set/list of chunk IDs considered correct for the query

A query is "hit" at rank k if any retrieved ID in the top-k is in gold_ids.
"""

from typing import Iterable, List, Sequence


def hit_at_1(retrieved_ids: Sequence[str], gold_ids: Iterable[str]) -> int:
    gold = set(gold_ids)
    return 1 if retrieved_ids and retrieved_ids[0] in gold else 0


def recall_at_k(retrieved_ids: Sequence[str], gold_ids: Iterable[str], k: int) -> float:
    gold = set(gold_ids)
    if not gold:
        return 0.0
    top_k = set(retrieved_ids[:k])
    return len(top_k & gold) / len(gold)


def reciprocal_rank(retrieved_ids: Sequence[str], gold_ids: Iterable[str]) -> float:
    gold = set(gold_ids)
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in gold:
            return 1.0 / rank
    return 0.0


def aggregate(per_query: List[dict]) -> dict:
    """Average a list of per-query metric dicts. Missing keys are skipped."""
    if not per_query:
        return {}
    keys = per_query[0].keys()
    out = {}
    for k in keys:
        vals = [q[k] for q in per_query if isinstance(q.get(k), (int, float))]
        out[k] = sum(vals) / len(vals) if vals else 0.0
    return out
