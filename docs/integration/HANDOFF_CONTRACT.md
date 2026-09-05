# Manual handoff contract

Handoffs are durable, human-reviewed summaries between StumbleBreach roles.
They index existing engagement records; they do not replace those records or
act as an instruction runner.

## Canonical location

Every engagement (bug bounty or CTF) stores one JSON object per handoff at:

```text
<engagement-root>/handoffs/<handoff_id>.json
```

The `handoff_id` is stable and the filename uses the same identifier. The
aggregate [`fixtures/handoffs.json`](fixtures/handoffs.json) file is test-only;
it is not a production handoff store.

Validate a production directory from its engagement root:

```sh
python3 scripts/validate_handoff.py handoffs/
```

The validator reports missing fields, malformed JSON, and malformed values. It
does not infer provenance, parent links, status, or evidence.

## Envelope

The machine-readable shape is [`handoff.schema.json`](handoff.schema.json).
Each new production envelope contains:

| Field | Meaning |
| --- | --- |
| `handoff_id` | Stable unique identifier; also the record filename. |
| `engagement`, `branch` | Owning engagement and branch. |
| `from_role`, `to_role` | Free-form role names for routing context; no role mapping is fixed here. |
| `parent_task` or `coverage_cell` | Task or queue cell being handed off. |
| `parent_handoff_id` | Optional direct parent record for a dynamic delegation tree or synthesized return. |
| `provenance` | Kind, source references, confidence, and review state for the summary. |
| `context` | Short context summary; detail remains in authoritative records. |
| `completed_work` | Bounded work actually completed. |
| `evidence_refs` | Paths and descriptions pointing to existing records or evidence. |
| `open_questions` | Unresolved questions, kept visible. |
| `requested_decision` | Decision requested from the operator, or an empty string. |
| `recommended_next_action` | Display-only prose; never a command. |
| `created_at` | RFC 3339 timestamp. |
| `status` | Lifecycle state from the schema. |

`provenance.source_refs` may name an authoritative path or a parent handoff
ID. `kind: unresolved` and an empty reference list are valid when the source
is not available; the missing source must remain visible in `open_questions`.
Role strings and parent links allow main-mastermind, sub-master, worker, Karma,
and return records without encoding a fixed delegation graph.

The schema keeps `provenance` and `parent_handoff_id` optional for legacy
envelopes so backpatching does not invent values. The production validator
requires `provenance`; pass `--legacy` only when checking an older envelope.
The existing `parent_task`/`coverage_cell` alternative remains unchanged.

## Authority and activity

Authoritative state remains, in order: scope and coverage/queue records,
finding readiness or CTF challenge records, then role-owned activity logs.
The handoff summarizes links and decisions. An operator still reviews a
handoff, changes queue state, and approves any continuation.

After creating, updating, reviewing, or returning a handoff, append one line
to the engagement activity log using:

```text
<ISO8601 timestamp> [<actor>/<role>] handoff=<handoff_id> parent=<id|none> action=<created|updated|reviewed|returned>
```

Bug-bounty engagements use `logs/activity.log`; CTF work uses
`challenges/<name>/activity.log`. The activity line is an audit record, not a
replacement for the handoff JSON.

## Reconstruction and safety

To reconstruct a handoff without chat history, load the envelope, identify its
engagement branch, follow `parent_handoff_id` when present, then inspect every
`evidence_refs` target and the authoritative scope/queue/coverage/finding or
challenge records named there. Missing references, `stale`, and `incomplete`
statuses remain visible.

The contract deliberately has no `command`, `dispatch`, `tool_call`,
`invoke_skill`, or autonomous action field. `recommended_next_action` cannot
start a role, tool, queue transition, or submission.
