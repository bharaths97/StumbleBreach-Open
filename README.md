# StumbleBreach

StumbleBreach is a reusable, file-backed tool for planning, conducting, and
reviewing authorized security research and technical exercises with AI coding
agents.

It combines reusable templates, explicit scope gates, separated planning and
worker roles, deterministic coverage tooling, and MCP tool-server source. It
is designed to work with Claude Code and Codex CLI while keeping private target
data and credentials out of the reusable tool.

StumbleBreach ships the **engine** — templates, harness, tools, and docs. The
**playbook** — the role instructions that drive an agent — is yours to author
and keep private. See [Engine and playbook](docs/ENGINE-AND-PLAYBOOK.md).

## Quickstart

```sh
git clone <this-repo> && cd StumbleBreach-Open
git config core.hooksPath .githooks
python3 scripts/harness/init_workspace.py --root .
```

The initializer wires the generic `roles/` playbook to `.claude/skills/` (and
Codex's `.agents/skills`) and enables the git hooks, without overwriting
anything. Then replace each `roles/<role>/SKILL.md` body with your own playbook
and read the docs below. Regenerate the engagement dashboard any time with
`python3 dashboard/generate.py > dashboard/index.html`.

## Start here

- [Overview](docs/OVERVIEW.md)
- [Engine and playbook](docs/ENGINE-AND-PLAYBOOK.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Harness](docs/HARNESS.md)
- [Roles](docs/ROLES.md)
- [Skills (the playbook layer)](docs/SKILLS.md)
- [Branching and private engagements](docs/BRANCHING.md)
- [Tooling and MCP setup](docs/TOOLING.md)
- [Workflow](docs/WORKFLOW.md)
- [Safety](docs/SAFETY.md)
- [Extending](docs/EXTENDING.md)
- [Claude Code and Codex CLI setup](docs/SETUP.md)

Use this project only with explicit authorization. Review the safety guidance
before creating a workspace or performing any technical activity.

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE).
