# Running IntelliRAGs

Setup, running the app, and running the evaluation harness. For *what* the project
is and what the eval showed, see the [README](../README.md).

---

## 1. Prerequisites

- **Python 3.13+** (developed on 3.13.5)
- A **Cohere API key** — free trial keys work. Get one at
  <https://dashboard.cohere.com/>. (Trial keys are rate-limited; the ingestion
  code retries on 429, but large ingests will be slow.)

---

## 2. Setup

From the repo root:

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create your .env from the template
cp .env.example .env
```

Then edit `.env` and set at least:

```env
COHERE_API_KEY=your_real_key_here
SECRET_KEY=any_long_random_string
```

`.env` is gitignored — never commit it.

---

## 3. Run the app

The app is two processes: the FastAPI backend and the Streamlit frontend. Run each
in its own terminal (both with the venv activated).

**Terminal 1 — API:**

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

- API root: <http://localhost:8000>
- Swagger docs: <http://localhost:8000/docs>

**Terminal 2 — dashboard:**

```bash
streamlit run src/dashboard/app.py
```

- Dashboard: <http://localhost:8501>

**Log in** with the built-in demo user:

| Username | Password |
|----------|----------|
| `demo`   | `demo123` |

> Defined in `src/api/main.py` (`get_fake_users_db`). This is a demo credential
> for local use only.

Then upload a document and ask questions. Uploaded files land in
`data/uploads/` (gitignored); their vectors go into the `documents` ChromaDB
collection.

---

## 4. Run the smoke-test scripts

These are imperative scripts (not `pytest` suites). Run them individually **from
the repo root** with the venv active. They call the real Cohere API and write
scratch `.txt` files into the repo root (gitignored).

```bash
python tests/test_document_processor.py   # extract → chunk → embed → store
python tests/test_rag.py                  # full ingest + retrieve + generate
python tests/test_security.py             # guardrail checks (no API key needed)
python tests/test_analytics.py            # analytics logging
python tests/test_api.py                  # hits the running API (start it first)
```

> `test_api.py` requires the API from step 3 to be running.

---

## 5. Run the evaluation harness

The harness builds a benchmark, runs the retriever + generator over it, and logs a
row to the `eval_runs` table in `analytics.db`. There are two ways to get a
benchmark.

### Option A — Open RAG Benchmark (what the baseline used)

Clone the dataset (needs `git-lfs`), then build the benchmark. This ingests the
papers' clean section text into an isolated `ragbench` collection:

```bash
git lfs install
git clone https://huggingface.co/datasets/vectara/open_ragbench data/ragbench_raw

python eval/load_ragbench.py \
    --ragbench-dir data/ragbench_raw \
    --n 150 \
    --reset
```

This writes `eval/benchmark_ragbench.jsonl`.

### Option B — synthesize from your own documents

Generate `(question, gold_answer)` pairs from chunks already in the `documents`
collection, then **hand-review the output** before trusting it:

```bash
python eval/synthesize.py --n 100 --out eval/benchmark.jsonl
```

### Sanity-check the gold mapping (recommended)

```bash
python eval/spot_check.py
```

Prints a few benchmark rows next to the chunks flagged as gold, so you can eyeball
whether the mapping is sensible.

### Run the eval

```bash
python eval/run.py \
    --tag baseline \
    --benchmark eval/benchmark_ragbench.jsonl \
    --collection ragbench \
    --top-k 5 \
    --notes "first baseline run"
```

Useful flags:

| Flag | Effect |
|------|--------|
| `--no-judge` | Skip the LLM judge — fast, retrieval metrics only |
| `--limit N` | Only evaluate the first N rows (quick iteration) |
| `--top-k K` | Change how many chunks are retrieved/ranked |
| `--collection NAME` | Which ChromaDB collection to evaluate against |

**Output:**
- A summary table in the terminal (Hit@1, Recall@5, MRR, faithfulness, correctness).
- Per-query detail: `eval/results/<timestamp>_<tag>.jsonl`.
- One row appended to `eval_runs` in `analytics.db`, viewable on the dashboard's
  Statistics page.

---

## 6. Resetting state

Both stores are regenerated on demand, so deleting them is safe:

```bash
rm -rf chroma_db/     # wipe all ingested vectors
rm -f analytics.db    # wipe analytics + eval history
```

---

## Troubleshooting

- **`Collection 'documents' not found`** — nothing has been ingested yet. Upload a
  document via the dashboard, or run a `tests/` ingest script first.
- **Cohere 429 / rate limit** — expected on trial keys during large ingests.
  Ingestion retries automatically (5× with 65 s backoff); just let it run.
- **Streamlit login doesn't redirect** — after logging in, click "Dashboard" or
  "Statistics" in the sidebar manually (behavior of the pinned Streamlit version).
- **`bcrypt`/`passlib` warning on startup** — harmless; pinned versions are
  compatible (see `requirements.txt`).
