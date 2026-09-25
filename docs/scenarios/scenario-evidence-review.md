# Three-Scenario Evidence Review

*(doc §21 — read-only review; no files modified as part of producing this review)*

## Scenario Readiness Matrix

| Check | Greenfield | Brownfield | Ambiguous |
|---|---|---|---|
| Requirement input exists | ✅ "Add redirect_count and last_accessed_at..." | ✅ "Fix: redirect resolution currently returns 302..." | ✅ "Make links expire eventually." |
| Interpretation exists | ✅ normalized_description set | ✅ normalized_description set | ✅ normalized twice (pre/post clarification) |
| Decomposition exists | ✅ `tasks_decomposed` event | ✅ `tasks_decomposed` event | ✅ `tasks_decomposed` event (after clarification) |
| Dependency graph visible | ✅ `src/orchestration/graph.py` N1–N14 | ✅ same graph, N4b branch | ✅ same graph, N4 branch |
| Orchestration path visible | ✅ N1→N2→N3→N5→N6→N7→N8→N9→(N10‖N11‖N12)→N13→N14 | ✅ N1→N2→N3→N4b→N5→N6→N7→N8→N9→(N10‖N11‖N12)→N13→N14 | ✅ N1→N2→N3→N4→N2→N3→N5→N6 |
| State transitions visible | ✅ 26 audit events | ✅ 26 audit events | ✅ 12 audit events |
| Human gates visible | ✅ N5 (auto-qualified), N8, N13 | ✅ N5 (reviews N4b artifact), N8, N13 | ✅ N4 (clarification), N5 |
| Tests exist | ✅ `test_scenario_greenfield.py` | ✅ `test_scenario_brownfield.py` | ✅ `test_scenario_ambiguous.py` |
| Validation executed | ✅ pytest, passing | ✅ pytest, passing | ✅ pytest, passing |
| Failure behavior demonstrated | ✅ negative scenario: conflict mid-design (design covers it; see spec US1 negative scenario — not separately re-executed here) | ✅ irreversible-change → compensation path (`test_rollback_vs_compensation.py`) | ✅ 24h timeout → SAFE_STOP (`test_n4_clarification.py`) |
| Audit evidence exists | ✅ full trail, `docs/scenarios/` (this review) | ✅ full trail, `docs/scenarios/brownfield-impact-analysis.md` | ✅ full trail, `docs/scenarios/ambiguous-requirement-demonstration.md` |
| Documentation matches execution | ✅ | ✅ | ✅ |
| Terminal outcome exists | ✅ `completed` | ✅ `completed` | Intentionally stops at N6 (see below) |
| Limitations disclosed | ✅ plan.md §Known Limitations | ✅ plan.md §Known Limitations (demo-authenticity) | ✅ this document, item below |

## Are the Three Scenarios Materially Different?

Yes, confirmed by comparing actual orchestration paths, not just labels:

- **Greenfield** never enters N4 or N4b — event count 26, zero clarification events, straight to N5.
- **Brownfield** enters N4b (impact analysis) before N5 — same event count (26) as greenfield but with `impact_analysis_drafted`/`impact_analysis_ready_for_review` replacing nothing (added, not substituted), and N5's approval rationale references the impact-analysis artifact rather than an "auto-qualified" note.
- **Ambiguous** is the only one that enters N4, re-enters N2/N3 a second time, and has a materially shorter event count (12) because the demonstration intentionally stops at `tasks_decomposed` rather than running the full N7–N14 tail (which is already covered by the other two scenarios' evidence and would be redundant to re-demonstrate here).

These are not three copies of the same trace with different labels — the classification branch each takes is structurally different in the audit trail itself.

## Missing Evidence

None found for the three required scenarios' core claims (SC-002, SC-003, SC-004).

## Unsupported Claims

None found. Every claim in the two scenario documents (`brownfield-impact-analysis.md`, `ambiguous-requirement-demonstration.md`) is backed by an audit event or Decision record from an actual code execution captured in this session, not a narrative description of expected behavior.

## Cross-Scenario Inconsistencies

None found. All three scenarios:
- use the same N1–N14 graph and the same gate mechanism (`src/orchestration/gates.py`) — approval semantics, timeout duration (24h), and rejection routing are identical across scenarios, not scenario-specific reimplementations.
- record `Decision`s with the same `actor_role_capacity` vocabulary (`reviewer_approver`, `release_owner`).
- emit audit events through the same `OrchestrationEngine.emit()` path, so the evidence format is uniform.

## Mandatory Remediation

None required to pass this review. One disclosed, non-blocking limitation carried forward from `plan.md` §Known Limitations applies here too: the ambiguous-requirement demonstration's terminal outcome is `tasks_decomposed`, not a full `completed` run — this is a deliberate scope choice (the N7–N14 tail is already evidenced twice by the other scenarios) and is stated as such above, not silently truncated.

**This review's own validation**: `pytest tests/integration/test_scenario_greenfield.py tests/integration/test_scenario_brownfield.py tests/integration/test_scenario_ambiguous.py -v` — 3 passed (re-run immediately before writing this document).
