# {{ENGAGEMENT_NAME}} — Project Instructions (Codex CLI)

Read `RULES.md` first — it has the full project layout, session-role
routing, and hard rules, and is the shared source of truth for both CLIs
used on this project. This file only holds what's specific to Codex CLI.

## Codex CLI specifics

- Permissions are not defined in this engagement — they live once,
  untracked, at the StumbleBreach project root (`.codex/config.toml`
  there, not here), covering every engagement branch. Select the
  profile matching this session's role (`overseer`/`worker`) at launch
  — flag naming may vary by Codex CLI version.
- `skill-library/` is a read-on-demand lookup shelf, not tied to either
  CLI's discovery mechanism — read `skill-library/INDEX.md` and the
  relevant file directly when needed, same as in Claude Code.
- Role duties themselves live only in the `ctf-mastermind`/`ctf-lavender-haze`/`ctf-vigilante-shit`
  Claude Code skills local to the `StumbleBreach` project root's
  `.claude/skills/` — not tracked in this repo. Codex CLI discovers the
  same skills through the untracked `.agents/skills` symlink after a
  session restart.

Nothing else differs from Claude Code on this project today — see
`CLAUDE.md` for the Claude-specific equivalent.
