# {{ENGAGEMENT_NAME}}

{{TARGET_DESCRIPTION}}, built to run with Claude Code and Codex CLI
interchangeably across multiple terminal sessions that coordinate
through files in this repo.

## First-time setup (only if using skill-library/)

If this competition benefits from external methodology/payload repos,
clone them into `skill-library/vendor/` and regenerate
`skill-library/INDEX.md`. Otherwise `skill-library/` stays empty and can
be ignored.

## Day-to-day usage

This entire template is engagement data. Commit it on the registered CTF
branch, never on `main`; the hub's pre-commit guard enforces that boundary.

After the planner has created `challenges/challenges.json`, scaffold its
challenge records with the shared hub script:

```sh
python3 scripts/ctf_scaffold.py --event-title "{{ENGAGEMENT_NAME}}"
```

1. Drop challenge description files into `challenges/intake/`, plus
   `general-rules.md` (the competition's rules — fill in the
   placeholder there before starting any challenge work).
2. Open one terminal, start Claude Code there, and invoke
   `/ctf-mastermind` — this is your **overseer session**.
3. Ask it to plan a challenge; it'll write
   `challenges/<name>/planning.md`, including the exact in-scope
   target(s) pulled from the intake file (copy the file set from
   `challenges/TEMPLATE/` for a new challenge).
4. When you need a **worker session** for hands-on testing, ask the
   overseer to write `challenges/<name>/instructions.md`. Open a new
   terminal in the same project, invoke `/ctf-lavender-haze` for initial artifact reconnaissance, then `/ctf-vigilante-shit` — it reads
   `challenges/<name>/instructions.md` itself to figure out which
   challenge it's scoped to.
5. Tool output gets saved manually — the session will give you the
   exact command; you run it and confirm. Every run gets one line in
   `challenges/<name>/activity.log`. Raw output goes in
   `challenges/<name>/results/` (git-ignored scratch space).
6. Once a flag is captured, ask the session to draft
   `challenges/<name>/report/report.md` from `REPORT_TEMPLATE.md` — the
   submission write-up. Screenshots go in
   `challenges/<name>/report/evidence/`. `report/` is tracked in git
   (unlike `results/`).
7. Work happens on a per-challenge branch off this engagement's branch;
   merge back when a challenge is checkpointed or done.

## Layout

See `RULES.md` for the full layout explanation and hard rules, and
`CLAUDE.md` / `AGENTS.md` for CLI-specific notes. Session roles come
from the `ctf-mastermind`/`ctf-lavender-haze`/`ctf-vigilante-shit` Claude Code skills, local to the
`StumbleBreach` project root's `.claude/skills/` (not tracked in this
repo, and not global — only discoverable while working inside that
project).
## Handoffs

Store one validated, human-reviewed record per file at
`handoffs/<handoff_id>.json`; see `handoffs/README.md`.
