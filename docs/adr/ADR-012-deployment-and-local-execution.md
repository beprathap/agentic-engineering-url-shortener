# ADR-012: Local Single-Process Deployment Model, No Containerization for v1

## Status
Accepted (Human Gate 4, 2026-09-24)

## Context
CON-002/AS-002 require local runnability without external managed infrastructure. A deployment/execution model must be chosen for how a reviewer actually runs the prototype.

## Decision Drivers
- Minimize setup friction for a reviewer reproducing the assessment.
- Avoid unjustified infrastructure (Planning Constraints).
- SQLite has no separate server process to orchestrate, unlike a client-server database.

## Options Considered

**Option A — Bare local process: `python -m venv`, `pip install`, `uvicorn src.api.app:app`** — SELECTED
- Advantages: Minimum possible setup (`quickstart.md`); no Docker daemon dependency for the reviewer; matches SQLite's own "no separate server" nature.
- Disadvantages: Less representative of a real containerized production deployment.
- Risks: Environment drift between reviewer machines (mitigated by pinning dependency versions in the manifest).
- Implementation impact: Minimal.
- Assessment implications: Fastest path for a reviewer to reproduce results within the 2-3 day timebox context.

**Option B — Docker Compose local stack**
- Advantages: More representative of production containerization practice; environment-independent.
- Disadvantages: Adds a Docker dependency and build step disproportionate to a single-process, single-file-database prototype; extra complexity the Planning Constraints explicitly discourage ("avoid unjustified distributed-system complexity") when there is no actual second service to orchestrate.
- Risks: None material; simply deferred, not rejected outright — noted as a reasonable brownfield enhancement.
- Implementation impact: Moderate (Dockerfile, compose file, image build/test in CI-equivalent).
- Assessment implications: Deferred to backlog (Plan §Planning Constraints); MAY be added later as a brownfield enhancement without touching application code.

## Decision
Bare local process execution for v1 (`uvicorn` directly). A `Dockerfile` is explicitly deferred to backlog, not rejected — it can be added later as a brownfield change without altering `src/`.

## Rationale
There is no second service to orchestrate (SQLite is embedded, not a server), so Docker Compose would add setup complexity with no corresponding benefit for this assessment's scope, directly contrary to the Planning Constraints' instruction to avoid unjustified complexity within the timebox.

## Consequences
- **Positive**: Fastest possible reviewer setup; fewer moving parts to debug if something goes wrong during review.
- **Negative**: Less production-realistic than a containerized deployment (disclosed as an intentional scope trade-off, not an oversight).
- **Operational**: Reviewer needs a local Python 3.12 interpreter; no Docker daemon required.
- **Testing**: CI-equivalent test execution (`pytest tests/`) runs identically to local development, no container build step in the loop.
- **Governance**: Adding containerization later is a backlog item (Plan §Planning Constraints), not a scope violation if omitted from the initial submission.

## Risks and Mitigations
- Risk: reviewer's local Python version differs from 3.12. Mitigation: pin the version in the dependency manifest and document it in `quickstart.md` prerequisites.

## Reversibility
High. Containerizing a bare-process Python app later is additive (a Dockerfile wrapping the existing entrypoint), not a rewrite.

## Traceability
- Requirements: CON-002, AS-002.
- Spec sections: Constraints, Assumptions.
- Plan sections: Technical Context, Planning Constraints (backlog).
- Expected task identifiers: Delivery Sequence slice 2 (Walking skeleton).

## Validation
Verified by: `quickstart.md`'s setup steps working end-to-end on a clean local Python 3.12 environment with no Docker dependency.
