# Engagement Journey

`journey.json` is the read-only graph projection used by the Dashboard's
reusable Journey view. It supports one visual for bug-bounty and CTF work:
nodes describe scope, targets, work, evidence, findings, challenges, and
handoffs; typed edges describe `pivot`, `follow-up`, `derived-from`,
`evidence-for`, `duplicate-of`, `blocked-by`, or `supersedes` relationships.

Every node, event, and edge carries provenance with source references,
confidence, and review state. A timestamp is an event ordering signal only;
the backpatch scanner never creates a causal edge from nearby timestamps.

## New engagements

Scaffold `templates/bugbounty/harness/journey.json` or
`templates/ctf/challenges/TEMPLATE/journey.json`, then append structured
events and edges as work happens. Existing scope, queue, findings, evidence,
and handoff records remain authoritative; Journey is a linked projection, not
a second source of truth.

## Older engagements

Run the read-only scanner from the engagement root:

```sh
python3 scripts/harness/journey_backpatch.py /path/to/engagement --type bug-bounty
```

It emits JSON to stdout. It reads legacy coverage, queue, findings, challenge
status, and activity records; it does not create or modify `journey.json` or
any source file. High-confidence source-linked candidates are marked
`review_state: candidate`. Missing or malformed records appear in `gaps`.
Ambiguous references and unparseable history appear in `review_queue` for an
agent or operator to inspect and explicitly accept, reject, or annotate.

The scanner may do mechanical extraction. It must not guess a pivot, finding
lineage, duplicate, or follow-up from timing or proximity. An agent can use
the review queue to gather context from the engagement and return a proposed
edge; an operator then decides whether that edge is written to the structured
Journey record.

Backpatching is therefore additive and fail-visible: old engagements continue
to load with explicit legacy gaps, while newer engagements get the current
schema. No candidate is auto-applied.
