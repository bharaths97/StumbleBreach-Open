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
- **Git harness** (`.githooks/`, `scripts/engagement_guard.py`,
  `scripts/resume_engagement.py`) — hooks and a branch guard that keep secrets
  and per-engagement data off shared branches and check workspace hygiene.
- **Dashboard** (`dashboard/generate.py`) — regenerates a read-only HTML view of
  engagement and CTF progress from live git state, without checking out a branch.
- **Starter playbook** (`roles/`) — a generic, fill-me-in `SKILL.md` per role,
  wired to `.claude/skills/` by the initializer. Replace each body with your own
  instructions; the shipped stubs contain no tradecraft.
- **Documentation** (`docs/`) — the operating model, roles, branch model,
  safety boundaries, and setup.

The engine is deliberately neutral. It ships no targets, no credentials, no
evidence, and only generic fill-me-in role stubs — never anyone's real operating
instructions. It is safe to clone and share as-is.

## The playbook (yours, kept private)

The playbook is the set of **role skills** that tell an agent how to behave in
each role — how your mastermind prioritizes, what your reconnaissance covers,
how your reviewer challenges a claim before it is promoted. You create it by
filling in the generic `roles/` stubs the engine ships; the initializer points
`.claude/skills/` at `roles/` so Claude Code reads them as skills and Codex CLI
finds them through the `.agents/skills` symlink. They encode judgement and
method, so your filled-in versions stay with you and out of any public remote.

[Skills](SKILLS.md) lists the role names the engine expects and shows the file
format. The names and one-line purposes are public; the instructions behind them
are not.

## How the two connect

```text
engine (this repo)                     playbook (your private setup)
------------------                     -----------------------------
templates/ scripts/ tools_mcp/ roles/  roles/<role>/SKILL.md (you fill in)
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
2. Run `python3 scripts/harness/init_workspace.py --root .` to wire the shipped
   `roles/` playbook to `.claude/skills/`, create the Codex `.agents/skills`
   symlink, and enable the hooks. It never overwrites files that already exist.
3. Edit each `roles/<role>/SKILL.md` to encode your own instructions. Keep
   planning, hands-on work, and review as distinct roles with explicit stop
   conditions.
4. Version the filled-in skills with your private operating setup — never in a
   public remote.

The result: one engine, shared and inspectable, driven by a playbook that
stays yours.
