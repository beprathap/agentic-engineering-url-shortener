# Agentic Software Engineering System: URL Shortener

A governed, stateful, non-linear agentic orchestration system, demonstrated using a URL shortener as the application domain. Built end-to-end via the SpecKit lifecycle (Constitution → Specify → Clarify → Plan → ADRs → Checklists → Tasks → Analyze → Implement → Converge → Final Assessment).

**Start here if you're reviewing this submission**: [`docs/REVIEWER_GUIDE.md`](docs/REVIEWER_GUIDE.md)

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                              # expect: 94 passed
uvicorn src.api.app:app --reload       # run the API locally
```

Full setup and validation scenarios: [`specs/001-agentic-url-shortener/quickstart.md`](specs/001-agentic-url-shortener/quickstart.md)

## Repository Map

| Path | Contents |
|---|---|
| `.specify/memory/constitution.md` | Governing principles (v1.0.0) |
| `specs/001-agentic-url-shortener/` | Spec, plan, research, data model, contracts, tasks |
| `docs/adr/` | 14 accepted Architecture Decision Records |
| `docs/scenarios/` | Live-execution evidence for the three required scenarios |
| `docs/assessment/` | Convergence report, final independent assessment, final engineering summary |
| `src/` | Implementation (domain, API, orchestration, policy, persistence, telemetry) |
| `tests/` | 94 tests (unit, contract, integration, orchestration-transition, security) |

**Release status**: READY WITH ACCEPTED LIMITATIONS — see [`docs/assessment/final-engineering-summary.md`](docs/assessment/final-engineering-summary.md).
