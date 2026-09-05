# Hunting playbook integration receipt

The private seed in `templates/bugbounty/harness/playbooks/` adapts a small
set of reviewed methodology patterns into StumbleBreach-owned guidance. It
does not vendor reference repositories, require a checkout or dependency at
runtime, grant authorization, select queue work, invoke roles, or replace
scope, coverage, readiness, Karma, evidence, or CTF records.

The shared checklist requires an ownership anchor and soft-404 control before
a signal is treated as an exposure. It gives workers one concrete hypothesis,
a selected queue-cell binding, bounded sibling follow-up, an A → B → C chain,
and a kill-fast stop condition. Negative controls and residual risk stay in
the handoff. Evidence rules cover principal identity, static/dynamic mode,
redaction, provenance, and curated evidence paths; existing deduplication and
prior-art checks remain required.

The seed currently covers web/API, binary, and blockchain work. Mobile is a
future reviewed adapter and is not implied by this package. CTF challenge,
flag, and artifact flow remains under `templates/ctf/` and CTF roles.

## Verification receipt

- Focused standard-library check: `python3 -m unittest tests/test_hunting_playbook.py`
- Scope: new playbook files, this receipt, and the focused test only.
- Result: coordinator must record the commit and final phase-level checks in
  the integration ledger before accepting this packet.
