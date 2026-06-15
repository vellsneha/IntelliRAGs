# IntelliRAGs

A hands-on **Retrieval-Augmented Generation (RAG)** project: upload documents, ask
questions, and get answers grounded in those documents — plus a real evaluation
harness to measure whether the retrieval and the answers are any good.

This is a **learning project**, not a production system. It implements a clean,
standard ("baseline") RAG pipeline end to end and pairs it with an honest
evaluation setup so the design choices can be measured rather than guessed at.
Where the numbers have caveats, they're spelled out below.

> **Setup and run instructions live in [`docs/RUNNING.md`](docs/RUNNING.md).**
> This file explains *what* the system is, *how* it's built, and *what the
> evaluation showed*.

---

## What it does

1. **Ingest** a document (PDF / DOCX / TXT) → extract text → split into chunks →
   embed each chunk → store the vectors in ChromaDB.
2. **Ask** a question → embed the question → find the most similar chunks
   (semantic search) → hand those chunks + the question to an LLM → return a
   grounded answer with its sources.
3. **Observe** — every query, upload, and piece of feedback is logged to a SQLite
   analytics database, viewable in the dashboard.

### The stack

| Layer | Choice | Notes |
|-------|--------|-------|
| API | FastAPI | REST endpoints + Swagger docs at `/docs` |
| UI | Streamlit | Login → upload/ask → statistics pages |
| Vector store | ChromaDB | Persistent, cosine similarity |
| Embeddings | Cohere `embed-english-v3.0` | 1024-dim vectors |
| Generation | Cohere `command-r7b-12-2024` | temperature 0.3 for Q&A |
| Analytics | SQLite (`analytics.db`) | queries, events, feedback, `eval_runs` |

### Key pipeline parameters

- **Chunking:** 500 words per chunk, 50-word overlap (`document_processor.py`)
- **Retrieval:** top-k = 5 by default, cosine distance
- **Embedding input types:** `search_document` at ingest, `search_query` at query
  time (Cohere's recommended asymmetric setup)

---

## Architecture

```
┌─────────────────┐
│  Streamlit UI   │  Login, upload, ask, statistics
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│   FastAPI API   │  auth (JWT) · upload · query · analytics · feedback
└────────┬────────┘
    ┌─────┴─────┐
    ▼           ▼
┌─────────┐ ┌─────────────┐
│Document │ │  Retriever  │
│Processor│ │   (RAG)     │
└────┬────┘ └──────┬──────┘
     │ embed       │ embed query + search
     ▼             ▼
┌─────────────────────┐
│      ChromaDB       │  vector storage
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│     Cohere API      │  embeddings + LLM generation
└─────────────────────┘
```

### API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET`  | `/` | Health check |
| `POST` | `/auth/login` | Get a JWT |
| `POST` | `/documents/upload` | Ingest a document |
| `POST` | `/query` | Ask a question (RAG) |
| `GET`  | `/analytics/summary` | Usage metrics |
| `POST` | `/feedback` | Rate an answer |

---

## Repository layout

```
IntelliRAGs/
├── README.md                  # this file — what & why
├── docs/
│   ├── RUNNING.md             # setup + run guide
│   └── MoreInfo.pdf           # supplementary project notes
├── src/
│   ├── api/main.py            # FastAPI app & endpoints
│   ├── dashboard/             # Streamlit app + pages/
│   ├── ingestion/
│   │   └── document_processor.py  # extract → chunk → embed → store
│   ├── retrieval/
│   │   └── retriever.py       # semantic search + answer generation
│   ├── analytics/tracker.py   # SQLite logging (incl. eval_runs)
│   └── guardrails/safety.py   # prompt-injection / jailbreak / PII checks
├── eval/                      # evaluation harness (see below)
│   ├── load_ragbench.py       # build a benchmark from Open RAG Benchmark
│   ├── synthesize.py          # alt: synthesize Q/A pairs from your own chunks
│   ├── run.py                 # run the harness, log a row to eval_runs
│   ├── metrics.py             # Hit@1, Recall@k, MRR
│   ├── judge.py               # LLM-as-judge (faithfulness, correctness)
│   ├── spot_check.py          # eyeball the gold-chunk mapping
│   └── results/               # per-run output
├── tests/                     # smoke-test scripts (run with python, not pytest)
├── data/uploads/              # runtime uploads (gitignored)
├── requirements.txt
└── .env.example               # copy to .env and add your keys
```

> **Not in git (gitignored):** `.env`, `chroma_db/`, `analytics.db`, the venv,
> the RAGBench dataset/PDFs under `data/`, and the scratch `.txt` files the test
> scripts write. These are either secret, large, or regenerated on demand.

---

## Evaluation

The interesting part of this project is that the RAG pipeline is **measured**, not
just demoed. The harness answers two questions:

- **Retrieval quality:** when we search, do we surface the right chunk? *(Hit@1,
  Recall@5, MRR)*
- **Answer quality:** is the generated answer grounded in the retrieved context,
  and does it match the reference answer? *(LLM-judged faithfulness & correctness)*

### How the benchmark is built

The benchmark is derived from Vectara's
[Open RAG Benchmark](https://huggingface.co/datasets/vectara/open_ragbench)
(research papers + queries + gold answers). `eval/load_ragbench.py`:

1. Deterministically samples N text-only queries (seeded, so runs are repeatable).
2. Ingests each referenced paper's **pre-extracted section text** through the
   *same* `DocumentProcessor` chunker + embedder the app uses — into an isolated
   `ragbench` ChromaDB collection (so eval never touches the `documents`
   collection).
3. Maps each query's gold `(doc_id, section_id)` to **our** chunk IDs using
   n-gram overlap between the gold section text and each chunk.

`eval/run.py` then runs the retriever over every query, computes the retrieval
metrics, generates an answer, scores it with the LLM judge, and appends one row
to the `eval_runs` table (tagged with the git SHA + config) for tracking over
time.

### Baseline results

Run `#2`, tag `ragbench-baseline`, git `badf46c`, 147 queries, top-k = 5
(full log: `eval/results/eval_1.txt`):

| Metric | Value | What it means |
|--------|-------|---------------|
| **Hit@1** | **0.463** | The top-1 retrieved chunk is a gold chunk ~46% of the time. |
| **Recall@5** | **0.687** | A gold chunk appears in the top-5 ~69% of the time. |
| **MRR** | **0.596** | Mean reciprocal rank ≈ 0.6 → when the gold chunk *is* found, it's usually ranked 1st–2nd. |
| **Faithfulness** | **4.31 / 5** | Answers are mostly grounded in the retrieved context (low hallucination). |
| **Correctness** | **4.29 / 5** | Answers mostly match the reference answers. |
| Retrieval latency | 0.21 s | Per query. |
| Generation latency | 2.19 s | Per query. |
| Wall time | ~482 s (8 min) | For all 147 queries, judge included. |

### How to read these honestly

- **The gold mapping is a heuristic.** Gold chunks are assigned by n-gram overlap,
  not human labeling, so there is real noise in the denominator. Treat these as a
  **relative baseline to beat**, not absolute ground truth.
- **The judge is biased toward the generator.** Both the judge and the generator
  are Cohere models, so faithfulness/correctness are best read as *trends across
  runs*, not as objective grades (this caveat is documented in `eval/judge.py`).
- **The most actionable signal is the ranking gap.** `Recall@5 − Hit@1 ≈ 0.22`:
  for ~22% of queries the right chunk is in the top-5 but *not* ranked first.
  That points at a **reranking** problem, not a chunking or retrieval-recall
  problem — so a reranker (e.g. Cohere Rerank) is the highest-leverage next step
  if the goal is to raise Hit@1.
- **3 / 147 judge calls failed** to parse (unescaped backslashes from LaTeX-y
  query text). The aggregate averages over the 144 successful judgements; the
  failures are tolerated rather than chased.

---

## Decisions & human-in-the-loop

The eval harness wasn't right on the first try. The choices below were made *after*
observing the harness misbehave — which is the point of having one.

1. **Ingest the dataset's clean corpus text, not the PDFs.**
   The first version downloaded each paper's PDF and ran it through PyPDF2. But
   PyPDF2's extraction differs from the dataset's clean extraction, so the n-gram
   comparison was comparing garbage against clean text and **median overlap
   collapsed to ~0** — no gold chunks could be mapped. Switching to the dataset's
   pre-extracted `corpus/<doc_id>.json` section text isolates the **chunker** as
   the variable under test. (See the `load_ragbench.py` module docstring.)

2. **Measure section-recall, not chunk-precision.**
   The overlap metric was flipped from "fraction of the *chunk's* n-grams found in
   the gold section" to "fraction of the *gold section's* n-grams captured by the
   chunk." A short gold section fully contained in a 500-word chunk *should* score
   1.0 — because the eval question is "does retrieving this chunk expose the
   answer?", not "is the chunk pure."

3. **`spot_check.py` for human QA of the mapping.**
   Before trusting the benchmark, `eval/spot_check.py` samples a few rows and
   prints each query next to the chunks the mapping flagged as gold, so the
   mapping quality can be eyeballed by a human rather than assumed.

4. **Added `ingest_text()` to share one code path.**
   So that eval ingests through the *same* chunker + embedder as production
   (rather than a parallel path that could silently diverge from what users hit).

5. **Cohere rate-limit retry.**
   Ingesting 100+ papers hit Cohere's trial rate limits, so `generate_embeddings`
   now retries on HTTP 429 (5 attempts, 65 s backoff) instead of crashing the run.

### Harness-engineering notes

- **Reproducible:** deterministic seeded sampling, isolated `ragbench` collection,
  every run stamped with git SHA + tag + config in `eval_runs`.
- **Inspectable:** per-query results written to `eval/results/<timestamp>_<tag>.jsonl`
  for drill-down.
- **Cheap modes:** `--no-judge` for retrieval-only sweeps, `--limit N` for quick
  iteration, `--top-k` to test ranking changes without re-ingesting.
- **Graceful degradation:** judge parse failures are logged and skipped, not fatal.

---

## Security & guardrails

`src/guardrails/safety.py` provides input/output checks for: prompt-injection
attempts, jailbreak patterns, PII leakage, and oversized input (a basic DoS
guard). The API uses JWT-based auth. These are baseline protections appropriate to
a learning project — not a substitute for a real security review.

---

## Credits

Built on [Cohere](https://docs.cohere.com/) (embeddings + LLM),
[ChromaDB](https://docs.trychroma.com/), [FastAPI](https://fastapi.tiangolo.com/),
and [Streamlit](https://docs.streamlit.io/). Benchmark derived from Vectara's
[Open RAG Benchmark](https://huggingface.co/datasets/vectara/open_ragbench).
