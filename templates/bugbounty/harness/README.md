# Vulnerability Harness

Before promoting a finding to `confirmed` or `submitted`, run
`python3 scripts/harness/validate_readiness.py findings/<slug>.md`. Use
`--write-manifest` once curated evidence is final; the normal command remains
read-only and verifies the resulting manifest and record links.

This directory persists coverage state for a bug-bounty engagement. It
does not replace scope controls, worker evidence collection, or overseer
sign-off. Read `coverage.json` at the start of a session; it is the
compact record of what has been considered for each area and attack
class.

## Protocol

1. After Recon identifies attacker-reachable areas, run
   `python3 scripts/harness/coverage_init.py`. It selects `web` by
   default or reads `TARGET_SURFACES` from `config/target.env`, then
   merges seeded cells without overwriting their status.
2. A worker performs the initial Hunt pass from seeded `not_started`
   cells. Before handing a candidate to the overseer, run
   `python3 scripts/harness/validate_schema.py findings/<slug>.md`.
3. The overseer runs `scripts/harness/dedup.py findings/<slug>.md`
   before reviewing duplicates and updates the corresponding coverage
   cell after the review.
4. On a user-requested Gapfill pass, the overseer appends `proposed`
   rows to `queue.md`. Only the user, or the overseer with the user's
   explicit instruction, changes a row to `selected` or `rejected`.
   After the initial pass, workers take only selected queue work.
5. Run `python3 scripts/harness/report.py` on request to regenerate the
   git-ignored `report.md` orientation summary.

## Adapters and commands

Each adapter specifies a taxonomy, Recon procedure, tool bindings, and
domain-specific finding fields. To add explicit areas beyond the scope
file's in-scope bullets, pass `--area id=description` one or more times:

```sh
python3 scripts/harness/coverage_init.py --area login-api='Login API endpoints'
python3 scripts/harness/report.py
```

The scripts default to paths relative to the current engagement root and
accept `--coverage`, `--scope`, `--findings-dir`, or `--output`
overrides where appropriate. They use only Python's standard library.
