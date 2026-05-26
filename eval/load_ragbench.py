"""
load_ragbench.py

Convert Vectara's Open RAG Benchmark (https://huggingface.co/datasets/vectara/open_ragbench)
into an eval/benchmark.jsonl file that eval/run.py can consume.

Pipeline:
  1. Read queries.json / qrels.json / answers.json / pdf_urls.json from a
     local clone of the dataset.
  2. Filter to text-only queries, deterministically sample N.
  3. Download the unique PDFs the sample references (cached on disk).
  4. Ingest those PDFs into a ChromaDB collection ('ragbench' by default)
     through the same DocumentProcessor production uses.
  5. Map each query's gold (doc_id, section_id) to a list of OUR chunk IDs
     using n-gram overlap between the gold section text and each chunk.
  6. Write eval/benchmark_ragbench.jsonl.

Prerequisite: clone the dataset first (requires git-lfs):
    git lfs install
    git clone https://huggingface.co/datasets/vectara/open_ragbench data/ragbench_raw

Usage:
    python eval/load_ragbench.py --ragbench-dir data/ragbench_raw --n 150 --reset
"""

import argparse
import json
import random
import sys
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import chromadb

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT / "src"))

from ingestion.document_processor import DocumentProcessor  # noqa: E402


COLLECTION_NAME = "ragbench"
PDF_DIR = ROOT / "data" / "ragbench_pdfs"
DEFAULT_OUT = ROOT / "eval" / "benchmark_ragbench.jsonl"


def load_metadata(ragbench_dir: Path) -> Dict:
    """Locate and load the 4 metadata JSONs. Tries pdf/arxiv/ first, then root."""
    candidates = [ragbench_dir / "pdf" / "arxiv", ragbench_dir]
    base = next((c for c in candidates if (c / "queries.json").exists()), None)
    if base is None:
        raise SystemExit(
            f"Couldn't find queries.json under {ragbench_dir}. "
            "Did `git clone` finish and were LFS pointers resolved?"
        )
    names = ["queries", "qrels", "answers", "pdf_urls"]
    out: Dict = {}
    for n in names:
        path = base / f"{n}.json"
        if not path.exists():
            raise SystemExit(f"Missing {path}")
        out[n] = json.loads(path.read_text(encoding="utf-8"))
    out["_corpus_dir"] = base / "corpus"
    out["_base"] = base
    return out


def sample_text_only(queries: Dict, qrels: Dict, n: int, seed: int) -> List[str]:
    candidates = [
        qid for qid, q in queries.items()
        if q.get("source") == "text" and qid in qrels
    ]
    random.seed(seed)
    random.shuffle(candidates)
    return candidates[:n]


def download_pdf(paper_id: str, url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        return True
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "ragbench-eval/0.1 (research)"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp, dest.open("wb") as f:
            f.write(resp.read())
        return True
    except Exception as e:
        print(f"  ! download failed for {paper_id}: {e}", file=sys.stderr)
        if dest.exists():
            dest.unlink()
        return False


def word_ngrams(text: str, n: int) -> Set[str]:
    words = text.lower().split()
    if len(words) < n:
        return set()
    return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}


def overlap_fraction(chunk_text: str, section_grams: Set[str], n: int) -> float:
    """Fraction of the chunk's n-grams that also appear in the gold section."""
    chunk_grams = word_ngrams(chunk_text, n)
    if not chunk_grams:
        return 0.0
    return len(chunk_grams & section_grams) / len(chunk_grams)


def get_section_text(corpus_dir: Path, doc_id: str, section_id) -> Optional[str]:
    p = corpus_dir / f"{doc_id}.json"
    if not p.exists():
        return None
    try:
        paper = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    sections = paper.get("sections", [])
    try:
        idx = int(section_id)
    except (TypeError, ValueError):
        return None
    if not (0 <= idx < len(sections)):
        return None
    return sections[idx].get("text", "") or ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ragbench-dir", required=True,
                    help="Path to the cloned vectara/open_ragbench repo")
    ap.add_argument("--n", type=int, default=150,
                    help="Number of queries to include in the benchmark")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--ngram", type=int, default=8,
                    help="N for n-gram overlap mapping (5-10 is reasonable)")
    ap.add_argument("--threshold", type=float, default=0.30,
                    help="Min fraction of chunk n-grams in gold section to count as gold")
    ap.add_argument("--reset", action="store_true",
                    help="Drop the 'ragbench' ChromaDB collection before ingesting")
    ap.add_argument("--skip-download", action="store_true",
                    help="Skip PDF download (assume cached). Useful when iterating on mapping.")
    ap.add_argument("--skip-ingest", action="store_true",
                    help="Skip ingestion (assume collection already populated).")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    ragbench_dir = Path(args.ragbench_dir).expanduser().resolve()
    if not ragbench_dir.exists():
        raise SystemExit(
            f"{ragbench_dir} does not exist.\n"
            "Clone the dataset first:\n"
            "  git lfs install\n"
            "  git clone https://huggingface.co/datasets/vectara/open_ragbench data/ragbench_raw"
        )

    print(f"Loading metadata from {ragbench_dir}...")
    meta = load_metadata(ragbench_dir)
    queries: Dict = meta["queries"]
    qrels: Dict = meta["qrels"]
    answers: Dict = meta["answers"]
    pdf_urls: Dict = meta["pdf_urls"]
    corpus_dir: Path = meta["_corpus_dir"]

    print(f"  queries={len(queries)}  qrels={len(qrels)}  answers={len(answers)}  "
          f"pdf_urls={len(pdf_urls)}")

    selected_qids = sample_text_only(queries, qrels, args.n, args.seed)
    print(f"Sampled {len(selected_qids)} text-only queries (seed={args.seed})")

    needed_doc_ids = sorted({qrels[qid]["doc_id"] for qid in selected_qids})
    print(f"They reference {len(needed_doc_ids)} unique PDFs")

    # ── Download PDFs ──────────────────────────────────────
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    downloaded: Dict[str, Path] = {}
    if args.skip_download:
        for doc_id in needed_doc_ids:
            dest = PDF_DIR / f"{doc_id}.pdf"
            if dest.exists() and dest.stat().st_size > 0:
                downloaded[doc_id] = dest
        print(f"Skip-download mode: {len(downloaded)} PDFs already cached")
    else:
        for i, doc_id in enumerate(needed_doc_ids, 1):
            url = pdf_urls.get(doc_id)
            if not url:
                print(f"  [{i}/{len(needed_doc_ids)}] no URL for {doc_id}")
                continue
            dest = PDF_DIR / f"{doc_id}.pdf"
            if download_pdf(doc_id, url, dest):
                downloaded[doc_id] = dest
                if i % 5 == 0 or i == len(needed_doc_ids):
                    print(f"  [{i}/{len(needed_doc_ids)}] ok ({len(downloaded)} cached)")
            time.sleep(0.4)
        print(f"Downloaded {len(downloaded)} / {len(needed_doc_ids)} PDFs")

    # ── Reset collection if requested ──────────────────────
    client = chromadb.PersistentClient(path=str(ROOT / "chroma_db"))
    if args.reset and not args.skip_ingest:
        try:
            client.delete_collection(COLLECTION_NAME)
            print(f"Deleted existing collection '{COLLECTION_NAME}'")
        except Exception:
            pass

    # ── Ingest PDFs ────────────────────────────────────────
    if not args.skip_ingest:
        processor = DocumentProcessor(collection_name=COLLECTION_NAME)
        print(f"Ingesting into ChromaDB collection '{COLLECTION_NAME}'...")
        for i, (doc_id, pdf_path) in enumerate(downloaded.items(), 1):
            try:
                result = processor.ingest_document(
                    str(pdf_path),
                    metadata={"doc_id": doc_id, "ragbench": True},
                )
                if i % 5 == 0 or i == len(downloaded):
                    print(f"  [{i}/{len(downloaded)}] {doc_id} → {result['chunks_created']} chunks")
            except Exception as e:
                print(f"  ! ingest failed for {doc_id}: {e}", file=sys.stderr)

    # ── Map gold sections → our chunk IDs ──────────────────
    print(f"Mapping gold sections to chunk IDs (n={args.ngram}, "
          f"threshold={args.threshold})...")
    collection = client.get_collection(COLLECTION_NAME)

    chunks_by_doc: Dict[str, List[Tuple[str, str]]] = {}

    def chunks_for(doc_id: str) -> List[Tuple[str, str]]:
        if doc_id not in chunks_by_doc:
            res = collection.get(where={"doc_id": doc_id}, include=["documents"])
            ids = res.get("ids") or []
            docs = res.get("documents") or []
            chunks_by_doc[doc_id] = list(zip(ids, docs))
        return chunks_by_doc[doc_id]

    out_rows = []
    dropped_no_section = 0
    dropped_no_chunks = 0
    overlap_stats = []

    for qid in selected_qids:
        rel = qrels[qid]
        doc_id = rel["doc_id"]
        section_id = rel.get("section_id", rel.get("section_index", 0))

        section_text = get_section_text(corpus_dir, doc_id, section_id)
        if not section_text:
            dropped_no_section += 1
            continue
        section_grams = word_ngrams(section_text, args.ngram)
        if not section_grams:
            dropped_no_section += 1
            continue

        gold_chunk_ids = []
        for cid, ctxt in chunks_for(doc_id):
            frac = overlap_fraction(ctxt, section_grams, args.ngram)
            overlap_stats.append(frac)
            if frac >= args.threshold:
                gold_chunk_ids.append(cid)

        if not gold_chunk_ids:
            dropped_no_chunks += 1
            continue

        out_rows.append({
            "query": queries[qid]["query"],
            "gold_answer": answers.get(qid, ""),
            "gold_chunk_ids": gold_chunk_ids,
            "source": str(PDF_DIR / f"{doc_id}.pdf"),
            "synthesized": False,
            "doc_id": doc_id,
            "section_id": section_id,
            "query_uuid": qid,
        })

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print()
    print("=" * 60)
    print(f"Wrote {len(out_rows)} rows to {out_path}")
    print(f"  dropped (gold section unreadable): {dropped_no_section}")
    print(f"  dropped (no chunk crossed threshold): {dropped_no_chunks}")
    if overlap_stats:
        overlap_stats.sort()
        mid = overlap_stats[len(overlap_stats) // 2]
        top = overlap_stats[-1]
        print(f"  overlap fractions: median={mid:.3f}  max={top:.3f}  "
              f"(threshold={args.threshold})")
    if out_rows:
        gold_counts = [len(r["gold_chunk_ids"]) for r in out_rows]
        print(f"  gold_chunk_ids/query: min={min(gold_counts)} "
              f"max={max(gold_counts)} avg={sum(gold_counts)/len(gold_counts):.2f}")
    print("=" * 60)
    print("Next:")
    print(f"  python eval/run.py --tag ragbench-baseline \\")
    print(f"      --benchmark {out_path} \\")
    print(f"      --collection {COLLECTION_NAME} \\")
    print(f"      --notes \"open_ragbench subset, chunk_size=500 overlap=50, top_k=5\"")


if __name__ == "__main__":
    main()
