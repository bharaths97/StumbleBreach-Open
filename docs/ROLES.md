# Roles

Use separate responsibilities so one agent does not silently choose scope, run
hands-on activity, and approve its own conclusion.

| Role | Responsibility |
|---|---|
| Planner | Sets up the engagement and maintains its visible work plan. |
| `bb-mastermind` / `ctf-mastermind` | Prioritize, check scope, route work, and accept or reject proposals for bug-bounty or CTF engagements. |
| `bb-lavender-haze` / `ctf-lavender-haze` | Reconnaissance, artifact mapping, and harness coverage seeding within explicit scope. |
| `bb-vigilante-shit` / `ctf-vigilante-shit` | Perform explicitly authorized hands-on hunting or challenge solving and record evidence. |
| `bb-archer` | Perform explicitly scoped smart-contract/blockchain review and validation. |
| `karma` | Challenge evidence, reproduction, impact, and report readiness before promotion. |
| `mirrorball` | Post-engagement retrospective: analyze process gaps, template fit, and tool improvements. |

Claude Code and Codex CLI can both follow this model. Configure each CLI using
its current official documentation, then give the session a clear role, scope,
and stop conditions. Role instructions should be versioned with your private
operating setup; this public repository documents the model and reusable tool.
