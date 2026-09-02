# {{ENGAGEMENT_NAME}} — Project Instructions (Claude Code)

Read `RULES.md` first — it has the full project layout, role routing, and
hard rules, and is the shared source of truth for both CLIs used on this
project. This file only holds what's specific to Claude Code.

## Claude Code specifics

- Permissions are not defined in this engagement — they live once,
  untracked, at the StumbleBreach project root (`.claude/settings.json`
  there, not here), covering every engagement branch. See the hub's own
  `RULES.md` if you need to see or change them.
- Roles are skills local to the StumbleBreach project root
  (`.claude/skills/`, same untracked location as permissions) — not
  project files, not global. Start a session with `/bb-mastermind`, `/bb-lavender-haze` for recon,
  `/bb-vigilante-shit`, or `/bb-archer` according to the explicit
  plan-item surface. Claude Code has no per-role profile switching at the
  permissions layer — this session's actual role is enforced by which
  skill was invoked, not by tool permissions. Codex CLI enforces the
  split more strictly via profiles at the permission layer — see
  `AGENTS.md` — and discovers the same role skills through `.agents/skills`.
- Web search/fetch is available and expected to be used for CVE/advisory
  lookups (RULES.md rule 10).

Nothing else differs from Codex CLI on this project today — see
`AGENTS.md` for the Codex-specific equivalent.
