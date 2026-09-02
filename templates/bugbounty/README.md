# {{ENGAGEMENT_NAME}}

{{TARGET_DESCRIPTION}}

## Layout

- `scope.md` — fill this in first. Target versions, IPs, authorization
  reference, out-of-bounds items. Nothing else should run until this is
  filled in.
- `logs/agent-scan-logs/`, `logs/network-captures/` — raw evidence.
  Git-ignored — scratch space, not the deliverable. Rename/repurpose as
  needed for this target's actual evidence shape.
- `logs/activity.log` — plain "who ran what, when" audit trail, tracked
  in git.
- `findings/` — one file per candidate finding, using
  `findings/TEMPLATE-finding.md`. This is what eventually becomes your
  submission.
- `findings/evidence/<finding-slug>/` — curated proof for a specific
  finding, tracked in git — distinct from the raw bulk logs above.
- `tools/` — one-time environment setup notes, per box/environment if
  more than one is involved.
- `config/target.env.example` — copy to `config/target.env` and fill in
  real IPs/ports/build numbers and, where applicable, blockchain scope
  fields. `target.env` is gitignored — don't commit real target details.

## Workflow

This entire template is engagement data. Commit it on the registered
bug-bounty branch, never on `main`; the hub's pre-commit guard enforces that
boundary.

## Bootstrap

After the planner has created this engagement branch from the template, use
the shared scaffold once to select the relevant adapters and seed the first
coverage areas. It creates only an ignored local `config/target.env` placeholder
when one does not yet exist, then calls the shared harness helper; it does not
create a branch, modify the registry, invent target values, or authorize work.

```sh
python3 scripts/bb_scaffold.py --root . --surface web \
  --area web:login-api="authenticated login API"
```

Repeat `--surface` and give each area its surface prefix for mixed work, for
example `--surface web --surface blockchain --area web:portal="customer portal"
--area blockchain:vault="Vault contract"`. Fill `scope.md` and the remaining
`config/target.env` values before any testing.

1. Fill in `scope.md` and `config/target.env`.
2. Start the overseer session first — in Claude Code, invoke
   `/bb-mastermind` (a skill local to the StumbleBreach project root's
   `.claude/skills/`, not global and not tracked in this repo); it
   should read `scope.md`, then propose a test plan before any worker
   session begins. For Codex, select the `overseer`/`worker` profile in
   the StumbleBreach project root's `.codex/config.toml` (not in this
   engagement — see `AGENTS.md` for the current Codex-side caveat on
   role duties).
3. Worker sessions execute one surface-tagged plan item: invoke `/bb-lavender-haze` for reconnaissance, then `/bb-vigilante-shit`
   for frontend/API/RPC-gateway work and `/bb-archer` for
   contract/fork/fuzz/invariant/static review. Mixed targets use separate
   worker sessions. Workers log evidence into `logs/` and `findings/`, and
   check back with the overseer before any
   action that installs, uninstalls, modifies, or deploys anything to a
   real target. Every run gets one line in `logs/activity.log`.
4. When a finding is credible, the overseer signs off before
   `findings/<finding-slug>.md` is created from
   `findings/TEMPLATE-finding.md`; evidence goes in
   `findings/evidence/<finding-slug>/`.
5. Commit small and often as work happens (`RULES.md` rule 9).
6. Before submitting anything to the program, cross-check `findings/`
   against the program scope/terms noted in `scope.md`.

## Guardrail (applies to both roles)

No agent takes any action that installs, uninstalls, patches, deploys a
configuration, or otherwise modifies a target system without explicit
human confirmation first. Read-only recon, log inspection, static binary
analysis, and traffic capture do not require confirmation. This line is
intentionally strict — loosening it means editing the `bb-mastermind`/
`bb-vigilante-shit` skills in the StumbleBreach project root's `.claude/skills/`,
not this repo, since that's where the guardrail text actually lives.
See `RULES.md` rule 2.
