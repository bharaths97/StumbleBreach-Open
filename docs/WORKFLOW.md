# Workflow

The framework uses a small, auditable lifecycle. The exact commands and
templates may vary by project, but the decision points should remain visible.

## Lifecycle

1. **Intake** — define the objective, authorized surfaces, restrictions, and
   expected deliverables. Fill in `scope.md` and `config/target.env`.
2. **Plan** — break the objective into small, reviewable work items and select
   the role responsible for each item. The mastermind owns `findings/plan.md`.
3. **Reconnaissance** — map only the approved surfaces and record assumptions.
   Seed the coverage harness (`coverage_init.py`) and populate the queue.
4. **Hunt or investigate** — perform scoped technical work and preserve useful
   evidence as you go. Only work items selected through `queue.md` proceed.
5. **Validate** — reproduce claims, check impact, and challenge possible false
   positives. Invoke `karma` for adversarial review before promotion.
6. **Deduplicate and gap-check** — group related observations and identify
   unreviewed areas for explicit human selection.
7. **Report and close out** — write the deliverable, record decisions, run
   `python3 scripts/engagement_guard.py closeout`, and protect or remove
   sensitive working data according to the project policy.

## Separation of duties

A planning or oversight session owns scope, prioritization, and acceptance. A
worker session performs the hands-on investigation and proposes evidence. A
reviewer challenges the proposal. No worker should approve its own finding or
expand scope silently.

## Evidence

Evidence should be reproducible, minimal, and attributable to a work item.
Separate raw scratch output from curated deliverables. Never put secrets,
personal information, or unauthorized target data in public documentation.
