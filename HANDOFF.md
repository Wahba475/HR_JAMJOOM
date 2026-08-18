   # CV Screener — Handoff

   **Goal of the next phase: deploy this to an Ubuntu server.**

   Everything below reflects the state as of 18 Aug 2026. The pipeline works
   end to end and has been measured against a 200-CV test set. What is *not*
   done is production hardening — that list is in section 6 and should be
   treated as blocking for anything internet-facing.

   ---

   ## 1. What this is

   HR uploads a batch of CV PDFs plus a job description and criteria. The
   system reads every CV, scores each against the role, re-compares the top
   candidates head-to-head, and returns a shortlist of N with a reason for
   each, links to the original PDFs, and a Google Sheet export.

   Built as a pitch artifact for Jamjoom Pharma.

   ---

   ## 2. Current state — what actually works

   Measured on a real 200-CV run (`ground_truth.csv` answer key, v2 set):

   | Metric | Result |
   |---|---|
   | Name extraction | 200/200 exact (100%) |
   | Email extraction | 200/200 exact (100%) |
   | Avg score — strong tier | 57.3 |
   | Avg score — medium tier | 36.6 |
   | Avg score — weak tier | 10.7 |
   | Shortlist precision | 9 of 10 from strong tier |
   | Upload (200 files) | 33s |
   | Pipeline (extract → score → rank → finalise) | 115s |
   | **Total** | **~2.5 min** |
   | Cost | $0.082 per 200 CVs (~$0.41 / 1,000) |

   Verified working: the full UI flow (form → 200-file drag-and-drop →
   progress → results), View/Download per CV, CSV export, CV zip download,
   live Google Sheet export, refresh persistence, and the back button.

   ### Models

   | Node | Model | Why |
   |---|---|---|
   | `score_cv` | `gpt-4.1-mini` | one call per CV; high volume, simple extraction |
   | `batch_rank` | `gpt-5.4-mini` | 3–5 calls per run; this is where judgment decides the shortlist |

   Both run at `temperature=0` with a fixed `RUN_SEED` for repeatability.

   ---

   ## 3. Bugs found and fixed (do not reintroduce)

   These were all found by running 200 CVs. None reproduce at 5 CVs.

   1. **Graph died at exactly 1 CV.** LangGraph evaluates a conditional edge
      *per source task*, not once after a `Send` fan-out completes. Ranking
      started while 199 CVs were still unscored and crashed sorting `None`.
      Fixed with barrier nodes (`texts_ready`, `scores_ready`) — a plain edge
      into a single node converges every branch first.
   2. **DB pool race.** Parallel branches each saw `_pool is None` and built
      their own pool, ~50 connections at once. Everything but the first branch
      hung forever. Fixed with an `asyncio.Lock` + double-check.
   3. **Sequential uploads.** 200 files took 220s of pure round-trip latency —
      longer than the AI work. Now concurrent (16 at a time) + one
      `executemany`: **33s**.
   4. **No concurrency cap.** `Send` fans out but does not throttle; without
      `max_concurrency` all 200 branches fire at once. Set to 20.
   5. **Score clustering.** 56 candidates tied at one score, so a hard top-N
      cut dropped 49 of them by arrival order — before the step that exists to
      tell them apart. Fixed with a rubric prompt (scores now spread 15–90)
      plus a tie-inclusive cutoff and deterministic `(score, candidate_id)`
      sort.
   6. **Stale-process trap.** On Windows `pkill` does not kill uvicorn, so a
      new server silently fails to bind while the old one keeps serving old
      code. Cost hours of false debugging. Use:
      `Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000 -State Listen).OwningProcess -Force`

   ---

   ## 4. Architecture

   ```
   Frontend (React + Vite, :5173)
      │  axios, all calls in src/context/RunContext.jsx
      ▼
   FastAPI (:8000)
      router → controller → service
      │
      ├── Neon Postgres        runs, candidates
      ├── Neon Object Storage  cv-uploads/{run_id}/{candidate_id}.pdf
      └── LangGraph pipeline
            START ──Send per CV──► extract_text   (PyMuPDF, no LLM)
                                       │
                                 texts_ready      (barrier)
                                       │
                  ──Send per CV──► score_cv       (gpt-4.1-mini, writes DB)
                                       │
                              scores_ready      (barrier)
                                       │
               ──Send per group──► batch_rank     (gpt-5.4-mini, groups of 12)
                                       │
                                 finalize_run     (shortlist / reject, one SQL tx)
   ```

   Only `score_cv` and later nodes touch the DB. `extract_text` fills
   in-memory state only. Progress ticks because `score_cv` commits per CV.

   ### Endpoints

   | Method | Path |
   |---|---|
   | POST | `/runs` |
   | POST | `/runs/{id}/cvs` |
   | POST | `/runs/{id}/start` |
   | GET | `/runs/{id}` |
   | GET | `/runs/{id}/results` |
   | POST · GET | `/runs/{id}/export` (CSV) |
   | POST | `/runs/{id}/sheet` (Google Sheet) |
   | GET | `/runs/{id}/cvs/download` (zip) |

   ---

   ## 5. Deploying to Ubuntu

   ### 5.1 Prerequisites on the server

   ```bash
   sudo apt update && sudo apt install -y docker.io docker-compose-plugin git
   sudo usermod -aG docker $USER   # log out and back in
   ```

   ### 5.2 Get the code

   ```bash
   git clone https://github.com/Wahba475/HR_JAMJOOM.git
   cd HR_JAMJOOM
   ```

   ### 5.3 Create the env file

   `.ENV` is gitignored, so it must be created on the server. Copy the
   template and fill it in:

   ```bash
   cp .env.example .ENV
   nano .ENV
   ```

   **Do not quote the values.** Docker's `--env-file` keeps quotes as part of
   the value — `AWS_REGION="us-east-2"` breaks boto3. Write
   `AWS_REGION=us-east-2`.

   Required:

   ```
   DATABASE_URL=postgresql://...neon.tech/neondb?sslmode=require
   AWS_ENDPOINT_URL_S3=https://....storage....neon.tech
   AWS_ACCESS_KEY_ID=...
   AWS_SECRET_ACCESS_KEY=...
   AWS_REGION=us-east-2
   BUCKET_NAME=cv1
   GPT_API_KEY=sk-proj-...
   ```

   Optional (Google Sheets export):

   ```
   GOOGLE_CREDENTIALS_PATH=/secrets/hr-jamjoom-sa.json
   GOOGLE_SHEET_ID=1Zx_aW3QZjYWvJadF96_MAtWK7tUaySqiIyAj8W7S5_Q
   ```

   Lock it down:

   ```bash
   chmod 600 .ENV
   ```

   ### 5.4 Database schema

   Run `schema.sql` once in the Neon SQL editor. It is idempotent-safe to
   read but will error if the tables already exist — that's fine, it means
   they're there.

   ### 5.5 Google service-account key (only if using Sheets export)

   ```bash
   sudo mkdir -p /opt/cv-screener/secrets
   sudo cp hr-jamjoom-sa.json /opt/cv-screener/secrets/
   sudo chmod 600 /opt/cv-screener/secrets/hr-jamjoom-sa.json
   ```

   ### 5.6 Build and run

   ```bash
   docker build -t cv-screener .

   docker run -d --name cv-api --restart unless-stopped \
   -p 8000:8000 \
   --env-file .ENV \
   -v /opt/cv-screener/secrets:/secrets:ro \
   cv-screener
   ```

   Drop the `-v` line if you're not using Sheets export.

   Check it:

   ```bash
   docker logs -f cv-api
   curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/docs   # expect 200
   ```

   ### 5.7 Frontend

   The React app is **not** containerised. Build it and serve the static
   files with nginx:

   ```bash
   cd cv-filter-frontend
   echo "VITE_API_URL=https://your-domain.com" > .env    # NOT localhost
   npm install
   npm run build          # outputs dist/
   sudo cp -r dist/* /var/www/cv-screener/
   ```

   `VITE_API_URL` is baked in at build time, so it must point at the server's
   public URL, not `localhost`. Rebuild if it changes.

   Minimal nginx config:

   ```nginx
   server {
      listen 80;
      server_name your-domain.com;

      client_max_body_size 200M;   # 200 CVs in one multipart request

      root /var/www/cv-screener;
      index index.html;
      location / {
         try_files $uri $uri/ /index.html;   # SPA routing
      }

      location /runs {
         proxy_pass http://127.0.0.1:8000;
         proxy_set_header Host $host;
         proxy_read_timeout 600s;    # uploads + long runs
      }
   }
   ```

   Then TLS:

   ```bash
   sudo apt install -y certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

   ### 5.8 Deployment gotchas

   - **`client_max_body_size`** — nginx defaults to 1 MB and will 413 a
   200-CV upload. The value above is essential.
   - **`proxy_read_timeout`** — a 200-CV upload takes ~33s and the default
   60s is tight if the server is slower than the dev laptop.
   - **Port already allocated** — `docker ps` and remove the old container;
   a second container cannot share port 8000.
   - **Never bake `.ENV` into the image.** `.dockerignore` excludes it and
   the image was verified to contain zero secrets. Keep it that way.

   ---

   ## 6. Not done — required before real traffic

   Ordered by severity. Items 1–3 are the ones I would not skip.

   1. **Uploads are fully buffered in RAM.** 1,000 real CVs ≈ 1 GB at once.
      Will OOM a small VPS. Needs streaming via `UploadFile.file` +
      `upload_fileobj`.
   2. **A crashed run stays `processing` forever.** No `failed` status is
      ever set, so a dead run is indistinguishable from a slow one. The DB
      columns (`runs.error`, `candidates.error`, `candidates.attempts`, and
      the `failed` enum value) are already migrated — the code just doesn't
      write them yet.
   3. **No retry.** One failed LLM call leaves `score=None` and that
      candidate is silently dropped from ranking. A real person disappears
      from the shortlist with no trace.
   4. **No authentication or rate limiting.** Anyone who can reach the URL
      can upload and spend your OpenAI credit. `config.py` already has
      `API_KEYS`, `RATE_LIMIT_PER_MINUTE`, and a
      `require_production_config()` that refuses to boot without auth when
      `ENVIRONMENT=production` — none of it is wired into `main.py` yet.
   5. **500s instead of 404s.** An unknown `run_id` raises rather than
      erroring cleanly, and FastAPI's 500 path skips CORS headers so the
      frontend shows nothing useful.
   6. **Storage leak.** A failed upload writes the PDF before the DB insert
      fails, orphaning bytes you still pay for.
   7. **`/start` takes ~10.7s.** Should return immediately; it currently
      builds the whole graph state inside the request.
   8. **Cross-group rank calibration.** `batch_rank` scores each group of 12
      independently, then `finalize_run` sorts across groups — but those
      scores share no reference. Fix is a final consolidation round over the
      top ~12. Deliberately deferred until after the demo.

   ### Also worth doing

   - **Rotate all credentials.** The Neon password, S3 keys, OpenAI key, and
   Google service-account key were all present in a local git history and
   the SA key passed through a chat transcript. Nothing leaked publicly
   (verified — `.ENV` returns 404 on GitHub), but rotate anyway.
   - **Scanned/image-only PDFs are not supported** — the extractor needs a
   real text layer. Would need OCR.
   - CV links in the Google Sheet expire after 7 days (SigV4 maximum).

   ---

   ## 7. Local development

   ```powershell
   # backend
   .\venv\Scripts\Activate.ps1
   uvicorn app.main:app --port 8000

   # frontend (second terminal)
   cd cv-filter-frontend
   npm run dev
   ```

   http://localhost:5173

   Test CVs live in `C:\Users\L\OneDrive\Desktop\test_cvs_medical_rep_200_v3\test_cvs`
   (200 PDFs; note v3 has **no** `ground_truth.csv` — the accuracy numbers in
   section 2 came from the v2 set, which has been replaced).

   ---

   ## 8. Repo

   `https://github.com/Wahba475/HR_JAMJOOM` — public, `main`.
   History was rewritten on 18 Aug to purge a committed `.ENV`; verified no
   credentials remain in any reachable commit.
