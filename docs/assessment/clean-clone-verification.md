# Clean-Clone Verification

**Performed**: 2026-09-25, immediately before tagging the final submission.

```bash
git clone /Users/josh/projects/agentic-engineering-url-shortener /tmp/clean-clone-verify
cd /tmp/clean-clone-verify
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

**Result**: `94 passed, 1 warning in 1.41s` — identical outcome to every other run in this session, from a completely fresh clone with no leftover state (no `.venv`, no `url_shortener.db`, no `__pycache__`).

Also verified the live server end-to-end from the same clean clone:

```bash
uvicorn src.api.app:app --port 8199 &
curl http://localhost:8199/healthz
# {"status":"ready","details":null}
curl -X POST http://localhost:8199/v1/links -H "Content-Type: application/json" -d '{"target_url": "https://example.com/clean-clone-test"}'
# {"short_code":"jC4cKvW", ...}
```

Both the test suite and the live API work exactly as documented in `README.md` and `docs/REVIEWER_GUIDE.md`, with no undocumented setup steps required. The temporary clone was deleted after verification (`rm -rf /tmp/clean-clone-verify`) — it is not part of this repository.
