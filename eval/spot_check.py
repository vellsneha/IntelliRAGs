"""Quick visual spot-check: sample 5 random rows from the benchmark and print
each query alongside the chunks the mapping flagged as gold."""

import json
import random
from pathlib import Path

import chromadb

ROOT = Path(__file__).resolve().parent.parent
BENCHMARK = ROOT / "eval" / "benchmark_ragbench.jsonl"
CHROMA_DIR = ROOT / "chroma_db"
COLLECTION = "ragbench"
N_SAMPLES = 5

random.seed(0)
col = chromadb.PersistentClient(path=str(CHROMA_DIR)).get_collection(COLLECTION)
rows = [json.loads(line) for line in BENCHMARK.open()]
print(f"Loaded {len(rows)} benchmark rows. Sampling {N_SAMPLES}...\n")

for row in random.sample(rows, N_SAMPLES):
    print("=" * 70)
    print("Q:", row["query"])
    gold_answer = (row.get("gold_answer") or "").replace("\n", " ")
    print("Gold answer:", gold_answer[:250] + ("..." if len(gold_answer) > 250 else ""))
    print(f"Mapped {len(row['gold_chunk_ids'])} gold chunk(s):")
    for cid in row["gold_chunk_ids"][:2]:
        got = col.get(ids=[cid], include=["documents"])
        docs = got.get("documents") or []
        if not docs:
            print(f"  [{cid[:24]}] (chunk not found)")
            continue
        text = docs[0].replace("\n", " ")
        print(f"  [{cid[:24]}] {text[:300]}...")
    print()
