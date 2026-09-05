# Handoffs

Store one production handoff object per file at `handoffs/<handoff_id>.json`.
Use the shared contract and validator from the engagement root:

```sh
python3 scripts/validate_handoff.py handoffs/
```

New records include `provenance` and either `parent_task` or `coverage_cell`;
use `parent_handoff_id` to link a parent or synthesized return. Role names stay
free-form so the delegation tree is not fixed by this template. Append the
corresponding `handoff=<handoff_id>` audit line to the relevant
`challenges/<name>/activity.log`.
