"""
Benchmark synthesizer.

Pulls a sample of chunks from ChromaDB, asks Cohere to generate one
(question, gold_answer) pair grounded in each chunk, and writes the pairs to
JSONL. Each line is:

    {
      "query": "...",
      "gold_answer": "...",
      "gold_chunk_ids": ["<chunk_id>"],
      "source": "<file path>",
      "synthesized": true
    }

Hand-review the output before using it as ground truth. Delete bad rows, flip
`synthesized` to false on rows you've vetted, and edit answers as needed.

Usage:
    python eval/synthesize.py --n 100 --out eval/benchmark.jsonl
"""

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

import chromadb
import cohere
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT / "src"))

load_dotenv()


SYNTH_PROMPT = """You are creating a benchmark question for a Retrieval-Augmented Generation system.

Given the passage below, produce ONE question that:
- Can be answered using ONLY this passage
- Is specific (not "what is this about?")
- Sounds like a real user query

Then produce a concise factual answer drawn ONLY from the passage.

Return strict JSON with this shape, and nothing else:
{{"question": "...", "answer": "..."}}

Passage:
\"\"\"
{passage}
\"\"\"
"""


def sample_chunks(n: int, seed: int = 42):
    client = chromadb.PersistentClient(path=str(ROOT / "chroma_db"))
    collection = client.get_collection(name="documents")
    total = collection.count()
    if total == 0:
        raise SystemExit("No chunks in ChromaDB. Ingest documents first.")
    # Pull everything (collections are typically small here) then sample.
    data = collection.get(include=["documents", "metadatas"])
    ids = data["ids"]
    docs = data["documents"]
    metas = data["metadatas"]
    pairs = list(zip(ids, docs, metas))
    random.seed(seed)
    random.shuffle(pairs)
    return pairs[: min(n, len(pairs))]


def synthesize_pair(co: cohere.Client, passage: str) -> dict | None:
    prompt = SYNTH_PROMPT.format(passage=passage[:2000])
    try:
        resp = co.chat(message=prompt, model="command-r7b-12-2024", temperature=0.4)
        text = resp.text.strip()
        # Strip code fences if the model added them
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        print(f"  ! synthesis failed: {e}", file=sys.stderr)
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50, help="Number of pairs to synthesize")
    ap.add_argument("--out", default=str(ROOT / "eval" / "benchmark.jsonl"))
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--sleep", type=float, default=0.2, help="Pause between API calls")
    args = ap.parse_args()

    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise SystemExit("COHERE_API_KEY not set")
    co = cohere.Client(api_key)

    chunks = sample_chunks(args.n, args.seed)
    print(f"Sampled {len(chunks)} chunks from ChromaDB. Synthesizing...")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with out_path.open("w", encoding="utf-8") as f:
        for i, (chunk_id, doc, meta) in enumerate(chunks, 1):
            print(f"[{i}/{len(chunks)}] {chunk_id}")
            pair = synthesize_pair(co, doc)
            if not pair or "question" not in pair or "answer" not in pair:
                continue
            row = {
                "query": pair["question"].strip(),
                "gold_answer": pair["answer"].strip(),
                "gold_chunk_ids": [chunk_id],
                "source": (meta or {}).get("source", ""),
                "synthesized": True,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
            time.sleep(args.sleep)

    print(f"\nWrote {written} rows to {out_path}")
    print("Next step: hand-review and edit before running eval/run.py")


if __name__ == "__main__":
    main()
