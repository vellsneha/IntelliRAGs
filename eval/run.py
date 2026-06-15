"""
Eval runner.

Loads eval/benchmark.jsonl, runs the current Retriever + generator on every
query, computes retrieval metrics (Hit@1, Recall@k, MRR) plus LLM-judge
scores (faithfulness, correctness), and appends one row to the eval_runs
table in analytics.db so you can track performance over time.

Usage:
    python eval/run.py --benchmark eval/benchmark.jsonl --tag baseline
    python eval/run.py --tag chunk-size-300 --top-k 5 --notes "smaller chunks"
    python eval/run.py --no-judge   # cheap retrieval-only run

The tag is how you label this run (e.g. "baseline", "rerank-v1"). Use it to
group runs in the Statistics page.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List

import cohere
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT / "src"))
sys.path.append(str(ROOT))

from analytics.tracker import AnalyticsTracker  # noqa: E402
from retrieval.retriever import Retriever  # noqa: E402

from eval.judge import judge_one  # noqa: E402
from eval.metrics import aggregate, hit_at_1, recall_at_k, reciprocal_rank  # noqa: E402

load_dotenv()


def load_benchmark(path: Path) -> List[Dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"  ! line {i} skipped: {e}", file=sys.stderr)
                continue
            if not row.get("query") or not row.get("gold_chunk_ids"):
                continue
            rows.append(row)
    return rows


def git_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL
        )
        return out.decode().strip()
    except Exception:
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", default=str(ROOT / "eval" / "benchmark.jsonl"))
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--recall-k", type=int, default=5,
                    help="k for Recall@k aggregate metric")
    ap.add_argument("--tag", required=True, help="Label for this run, e.g. 'baseline'")
    ap.add_argument("--notes", default="")
    ap.add_argument("--collection", default="documents",
                    help="ChromaDB collection to evaluate against (e.g. 'ragbench')")
    ap.add_argument("--no-judge", action="store_true",
                    help="Skip the LLM-judge step (retrieval metrics only)")
    ap.add_argument("--limit", type=int, default=0,
                    help="Only evaluate the first N rows (0 = all)")
    ap.add_argument("--out", default=str(ROOT / "eval" / "results"),
                    help="Directory for per-row JSONL results")
    args = ap.parse_args()

    bench_path = Path(args.benchmark)
    if not bench_path.exists():
        raise SystemExit(f"Benchmark file not found: {bench_path}")

    rows = load_benchmark(bench_path)
    if args.limit:
        rows = rows[: args.limit]
    if not rows:
        raise SystemExit("Benchmark is empty.")
    print(f"Loaded {len(rows)} queries from {bench_path}")

    retriever = Retriever(collection_name=args.collection)
    co = None
    if not args.no_judge:
        api_key = os.getenv("COHERE_API_KEY")
        if not api_key:
            raise SystemExit("COHERE_API_KEY required for judge (or use --no-judge)")
        co = cohere.Client(api_key)

    per_query = []
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_ts = time.strftime("%Y%m%dT%H%M%S")
    detail_path = out_dir / f"{run_ts}_{args.tag}.jsonl"
    detail_f = detail_path.open("w", encoding="utf-8")

    start = time.time()
    for i, row in enumerate(rows, 1):
        q = row["query"]
        gold = row["gold_chunk_ids"]
        gold_answer = row.get("gold_answer", "")

        t0 = time.time()
        retrieved = retriever.retrieve(q, top_k=args.top_k)
        retrieved_ids = [d["id"] for d in retrieved]
        retrieval_latency = time.time() - t0

        row_metrics = {
            "hit_at_1": hit_at_1(retrieved_ids, gold),
            f"recall_at_{args.recall_k}": recall_at_k(retrieved_ids, gold, args.recall_k),
            "mrr": reciprocal_rank(retrieved_ids, gold),
            "retrieval_latency_s": retrieval_latency,
        }

        gen_result = None
        judge_result = {}
        if not args.no_judge:
            t1 = time.time()
            gen_result = retriever.generate_answer(q, retrieved)
            gen_latency = time.time() - t1
            row_metrics["gen_latency_s"] = gen_latency
            assert co is not None
            judge_result = judge_one(
                co, q, gold_answer, gen_result["answer"], retrieved
            )
            row_metrics["faithfulness"] = judge_result.get("faithfulness", 0)
            row_metrics["correctness"] = judge_result.get("correctness", 0)

        per_query.append(row_metrics)
        detail_f.write(json.dumps({
            "query": q,
            "gold_chunk_ids": gold,
            "gold_answer": gold_answer,
            "retrieved_ids": retrieved_ids,
            "predicted_answer": gen_result["answer"] if gen_result else None,
            "metrics": row_metrics,
            "judge": judge_result,
        }, ensure_ascii=False) + "\n")

        if i % 10 == 0 or i == len(rows):
            print(f"  [{i}/{len(rows)}] hit@1 so far = "
                  f"{sum(p['hit_at_1'] for p in per_query)/len(per_query):.3f}")

    detail_f.close()
    wall = time.time() - start

    metrics = aggregate(per_query)
    metrics["num_queries"] = len(per_query)
    metrics["wall_seconds"] = round(wall, 2)

    config = {
        "top_k": args.top_k,
        "recall_k": args.recall_k,
        "judge_enabled": not args.no_judge,
        "embed_model": "embed-english-v3.0",
        "gen_model": "command-r7b-12-2024",
        "benchmark": str(bench_path),
        "collection": args.collection,
        "limit": args.limit,
    }

    tracker = AnalyticsTracker(db_path=str(ROOT / "analytics.db"))
    run_id = tracker.log_eval_run(
        tag=args.tag,
        config=config,
        metrics=metrics,
        num_queries=len(per_query),
        benchmark_path=str(bench_path),
        git_sha=git_sha(),
        notes=args.notes,
    )

    print("\n" + "=" * 60)
    print(f"Run #{run_id}  tag={args.tag}  git={git_sha() or 'n/a'}")
    print("=" * 60)
    for k, v in metrics.items():
        if isinstance(v, float):
            print(f"  {k:24s} = {v:.4f}")
        else:
            print(f"  {k:24s} = {v}")
    print(f"\nPer-query details: {detail_path}")
    print(f"Logged to analytics.db (eval_runs.id = {run_id})")


if __name__ == "__main__":
    main()
