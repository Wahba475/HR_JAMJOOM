# CV Screener

Filters a large batch of CVs down to a shortlist. You give it a job
description, hiring criteria, and a folder of PDFs; it reads every CV,
scores them against the role, compares the top candidates head-to-head,
and returns the best N with a reason for each.

Built for Jamjoom Pharma's HR team.

---

## What it does

1. **Upload** — drag in any number of PDF CVs.
2. **Extract** — pulls the text out of each PDF (no AI, just parsing).
3. **Score** — one AI call per CV: extracts name and email, scores the
   candidate 0–100 against the job, and writes a one-line rationale.
4. **Rank** — the top candidates are then compared *against each other* in
   small groups. This matters: scored in isolation, a dozen good CVs all
   land on "85". This pass breaks those ties into a real ordering.
5. **Shortlist** — the top N are marked shortlisted, everyone else rejected.
6. **Review** — results page with scores, rationales, and the original PDFs.

Steps 2–4 run in parallel, so 200 CVs take about two minutes rather than
an hour.

---

## Measured results

Tested end-to-end on 200 CVs with a known-correct answer key:

| Metric | Result |
|---|---|
| Name extraction | 200/200 exact (100%) |
| Email extraction | 200/200 exact (100%) |
| Avg score — strong candidates | 57.3 |
| Avg score — medium candidates | 36.6 |
| Avg score — weak candidates | 10.7 |
| Shortlist precision | 9 of 10 from the strong tier |
| Total time | ~2.5 min (33s upload + 115s pipeline) |
| Cost | $0.08 per 200 CVs (~$0.41 per 1,000) |

---

## Setup

### 1. Database

Create a Neon Postgres project, then paste [`schema.sql`](schema.sql) into
its SQL editor and run it. That creates the two tables.

### 2. Storage

In the same Neon project, enable Object Storage and create a bucket. Copy
the endpoint and credentials it gives you.

### 3. Environment

```bash
cp .env.example .ENV
```

Fill in the database URL, storage credentials, and your OpenAI API key.

### 4. Backend

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1        # source venv/Scripts/activate on Git Bash
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

### 5. Frontend

```powershell
cd cv-filter-frontend
npm install
npm run dev
```

Open **http://localhost:5173**.

---

## How the code is laid out

```
app/
├── main.py                 FastAPI app
├── config.py               reads environment variables
├── routers/                URL → function mapping
├── controllers/            request parsing, response shaping
├── services/
│   ├── run_service.py      upload, start, fetch results
│   ├── storage.py          save/read PDFs (swap this to change storage)
│   └── sheets_export.py    CSV export, Google Sheets push, CV zip
├── db/                     connection pool + raw SQL
└── graph/
    ├── graph.py            wires the pipeline together
    ├── prompts.py          the AI instructions
    └── nodes/
        ├── extract_text.py read the PDF
        ├── score_cv.py     score one CV
        ├── batch_rank.py   compare a group of CVs
        └── finalize_run.py pick the shortlist

cv-filter-frontend/src/
├── pages/                  Setup, Progress, Results
├── components/             dropzone, cards, progress ring
└── context/RunContext.jsx  all API calls live here
```

The pipeline is a [LangGraph](https://langchain-ai.github.io/langgraph/)
graph. Each node is one small function in its own file.

---

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/runs` | create a run |
| POST | `/runs/{id}/cvs` | upload PDFs |
| POST | `/runs/{id}/start` | start the pipeline |
| GET | `/runs/{id}` | progress (polled by the UI) |
| GET | `/runs/{id}/results` | the shortlist |
| POST | `/runs/{id}/export` | download shortlist as CSV |
| POST | `/runs/{id}/sheet` | push shortlist to a Google Sheet |
| GET | `/runs/{id}/cvs/download` | download all shortlisted PDFs as a zip |

Interactive docs at http://localhost:8000/docs while the server runs.

---

## Costs

Two models, chosen per job:

- **Scoring** uses `gpt-4.1-mini` — one call per CV, so volume is high but
  the task is simple extraction.
- **Ranking** uses `gpt-5.4-mini` — only a few calls per run, but it's the
  step where judgment actually decides who gets shortlisted, so it's worth
  the stronger model.

Roughly **$0.41 per 1,000 CVs**. A typical 50-CV posting costs about 2 cents.

---

## Security

**Never commit `.ENV`.** It holds live database, storage, and API
credentials. It's in `.gitignore` — keep it that way, and keep Google
service-account JSON files outside the repo entirely.

### Not yet production-ready

This runs correctly, but the following are still open and should be
addressed before it faces real traffic:

- **No authentication** — anyone who can reach the API can upload and spend
  your OpenAI credit. Keep it bound to `127.0.0.1`.
- **Uploads are held in memory** — a very large batch could exhaust RAM.
- **A crashed run stays "processing"** — there's no `failed` state yet, so a
  failure looks like a slow run.
- **No retry** — if one CV's AI call fails, that candidate is dropped from
  ranking silently.
- **Some errors return 500 instead of 404** — e.g. an unknown run id.

---

## Notes

- Scanned/image-only PDFs won't work — the text extractor needs a real text
  layer. OCR would be needed for those.
- Every candidate and file is scoped to a `run_id`, so multiple job postings
  never mix.
- Nothing is deleted between runs; past runs stay queryable as an audit trail.
