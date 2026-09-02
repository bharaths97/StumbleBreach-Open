# Coverage harness

The bug-bounty template contains a file-backed coverage harness. Its purpose is
to make coverage visible without asking an agent to remember every surface and
attack class from conversation alone.

| Component | Purpose |
|---|---|
| `coverage.json` | Coverage grid by area and attack class. |
| `queue.md` | Human selection gate for proposed work. |
| `adapters/` | Domain-specific recon and schema guidance. |
| `scripts/harness/coverage_init.py` | Seeds or merges the coverage grid. |
| `scripts/harness/validate_schema.py` | Checks a finding's required fields. |
| `scripts/harness/dedup.py` | Highlights likely duplicate candidates. |
| `scripts/harness/report.py` | Produces the coverage/report roll-up. |

The normal loop is:

```text
Recon -> Hunt -> Validate -> Gapfill -> Deduplicate -> Report
```

For a new bug-bounty engagement, run `scripts/bb_scaffold.py` after the
template has been copied to its private branch. Select one or more available
adapters and name the initial areas. The command creates an ignored local
`config/target.env` from the safe example when needed, sets only the selected
surface names, and asks the shared `coverage_init.py` helper to seed coverage.
It never creates branches, registers engagements, adds target details, or
authorizes testing.

Agents may propose work, but a human or designated overseer selects it through
the queue. The scripts are deterministic helpers; they do not grant authority
to test a system or submit a finding.

The adapters ship with domain-specific taxonomies (web, blockchain, binary).
If an engagement's attack surface does not fit an existing adapter -- for
example, OS policy bypass or sandbox escape work -- extend the taxonomy or
create a new adapter rather than running without coverage tracking.
