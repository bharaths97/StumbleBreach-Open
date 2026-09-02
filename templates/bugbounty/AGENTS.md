# {{ENGAGEMENT_NAME}} — Project Instructions (Codex CLI)

Read `RULES.md` first — it has the full project layout, role routing, and
hard rules, and is the shared source of truth for both CLIs used on this
project. This file only holds what's specific to Codex CLI.

## Codex CLI specifics

- Permissions are not defined in this engagement — they live once,
  untracked, at the StumbleBreach project root (`.codex/config.toml`
  there, not here), covering every engagement branch with `overseer`
  and `worker` profiles. Select the one matching this session's role at
  launch (flag naming may vary by Codex CLI version).
- Network is enabled for both profiles — both roles are expected to do
  live CVE/NVD/Exploit-DB/advisory research (RULES.md rule 10).
- Role duties live in the `bb-mastermind`, `bb-lavender-haze`, `bb-vigilante-shit`, and
  `bb-archer` skills local to the StumbleBreach project root's
  `.claude/skills/`. Codex discovers the same skills through the
  untracked `.agents/skills` symlink after a session restart. Choose
  `bb-lavender-haze` for recon, `bb-vigilante-shit` for web/API work and `bb-archer` for contract,
  fork, fuzz, invariant, or static blockchain work; do not switch a
  worker's role mid-task.

Nothing else differs from Claude Code on this project today — see
`CLAUDE.md` for the Claude-specific equivalent.
