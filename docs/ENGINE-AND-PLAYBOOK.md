# Engine and playbook

StumbleBreach separates two things that are usually tangled together in an
AI-assisted testing setup: the reusable machinery, and the private operating
instructions that drive it. We call them the **engine** and the **playbook**.

## The engine (this repository)

The engine is everything in this public repository:

- **Templates** (`templates/`) — the file layout for a bug-bounty or CTF
  workspace: rules, scope placeholders, finding and report structure, harness
  skeleton, and the adapter notes for web, binary, system, and blockchain work.
- **Harness scripts** (`scripts/harness/`, `scripts/bb_scaffold.py`,
  `scripts/ctf_scaffold.py`) — deterministic, mostly read-only tooling that
  seeds coverage, validates finding structure, flags likely duplicates, and
  renders roll-ups. The harness never decides what to test.
- **MCP tool source** (`tools_mcp/`) — source for the `recon`, `webapp`, and
  `blockchain` tool registries and their scope guard, plus a doctor that reports
  what is missing on the local machine.
- **Documentation** (`docs/`) — the operating model, roles, branch model,
  safety boundaries, and setup.

The engine is deliberately neutral. It ships no targets, no credentials, no
evidence, and no operating instructions. It is safe to clone and share as-is.

## The playbook (yours, kept private)

The playbook is the set of **role skills** that tell an agent how to behave in
each role — how your mastermind prioritizes, what your reconnaissance covers,
how your reviewer challenges a claim before it is promoted. These live untracked
in `.claude/skills/` and are read by Claude Code as skills and by Codex CLI
through the `.agents/skills` symlink. They encode judgement and method, so they
stay with you and out of any public remote.

[Skills](SKILLS.md) lists the role names the engine expects and shows the file
format. The names and one-line purposes are public; the instructions behind them
are not.

## How the two connect

```text
engine (this repo)                     playbook (your private setup)
------------------                     -----------------------------
templates/  scripts/  tools_mcp/       .claude/skills/<role>/SKILL.md
        |                                        |
        |   invoked as a role  <----------------- .agents/skills (Codex symlink)
        v
a scaffolded engagement workspace  <--  a role session with scope + stop rules
        |
        v
coverage, evidence, findings  ---->  karma review  ---->  reported result
```

An agent session starts by adopting a role from the playbook, then operates
inside a workspace scaffolded from the engine's templates, using the engine's
harness and tools. The role decides; the harness records and checks.

## Connecting your own playbook

1. Clone this repository and enable the hooks (see [Setup](SETUP.md)).
2. Run `python3 scripts/harness/init_workspace.py --root .` to create the
   `.claude/skills/` layout, the Codex `.agents/skills` symlink, and an empty
   stub for each role. It never overwrites files that already exist.
3. Edit each `SKILL.md` to encode your own instructions. Keep planning,
   hands-on work, and review as distinct roles with explicit stop conditions.
4. Version the filled-in skills with your private operating setup — never in a
   public remote.

The result: one engine, shared and inspectable, driven by a playbook that
stays yours.
