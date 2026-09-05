# Dashboard read-model contract

The dashboard's first contract is a JSON read model. It is observational: it
does not invoke a role, change a queue, run a tool, check out a branch, or
submit a finding. The future local server exposes only `GET` routes:

| Route | Model field | Purpose |
|---|---|---|
| `/api/health` | `health` | Tool/MCP doctor report, including missing or unreadable state |
| `/api/overview` | `overview` | Counts and separated view counts |
| `/api/engagements/{branch}` | `engagements[]` | One bug-bounty or CTF record |
| `/api/handoffs` | `handoffs` | Durable handoff envelopes and statuses |
| `/api/tooling` | `tooling` | Sanitized receipt summaries only; raw output is never returned |
| `/api/run-status` | `run_status` | Observational runner state; `unknown` while runner work is on hold |

The source registry is `main:ENGAGEMENTS.md`. Branch records are read from
Git objects with `git show` and `git ls-tree`; the read model never checks out
an engagement. Missing, malformed, stale, and unsupported records remain
visible through `state`/`data_state` rather than being silently dropped.

Bug-bounty and CTF records have distinct `analysis.view` shapes. Scope,
coverage, queue, findings, challenge status, and activity remain references to
their existing authoritative records. Handoff status remains descriptive;
the model contains no command, dispatch, tool-call, or state-changing field.
