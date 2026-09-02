# {{ENGAGEMENT_NAME}} — Project Instructions (Claude Code)

Read `RULES.md` first — it has the full project layout, session-role
routing, and hard rules, and is the shared source of truth for both CLIs
used on this project. This file only holds what's specific to Claude Code.

## Claude Code specifics

- Permissions are not defined in this engagement — they live once,
  untracked, at the StumbleBreach project root (`.claude/settings.json`
  there, not here), covering every engagement branch. See the hub's own
  `RULES.md` if you need to see or change them.
- Roles are skills local to the StumbleBreach project root
  (`.claude/skills/`, same untracked location as permissions) — not
  project files, not global. Start a session with `/ctf-mastermind`, `/ctf-lavender-haze` for recon, or
  `/ctf-vigilante-shit`.
- `skill-library/` is a read-on-demand lookup shelf, not
  auto-discovered — sessions read the specific file they need directly,
  every time, rather than anything being promoted into a
  Claude-Code-discoverable location.

Nothing else differs from Codex CLI on this project today — see
`AGENTS.md` for the Codex-specific equivalent.
