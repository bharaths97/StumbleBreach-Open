# Skills (the playbook layer)

StumbleBreach ships the **engine** — templates, harness scripts, MCP tool
source, and documentation — plus a **generic starter playbook** under `roles/`:
one fill-me-in `SKILL.md` per role. It does **not** ship a real playbook. Your
real playbook is what you get by replacing each stub body with your own
instructions for how an agent plans, hunts, and reviews on your terms.
`init_workspace.py` wires `roles/` to `.claude/skills/` (Claude Code) and to
Codex CLI through the `.agents/skills` symlink, so editing `roles/<role>/SKILL.md`
is the single place you fill in. Keep those filled-in files private — out of any
public remote. The engine stays neutral and shareable; the tradecraft you add
does not.

See [Engine and playbook](ENGINE-AND-PLAYBOOK.md) for why the split exists and
how the two layers connect.

## Role roster

These are the role names the engine's templates and documentation refer to. The
name and one-line purpose are public; the actual instructions behind each are
authored privately by the operator. `bb-*` roles serve bug-bounty engagements,
`ctf-*` roles serve capture-the-flag work, and the rest are shared.

| Skill | Purpose (one line) |
|---|---|
| `pentest-planner` | Set up an engagement branch and maintain its work plan; no hands-on testing or sign-off. |
| `bb-mastermind` / `ctf-mastermind` | Prioritize, check scope, route work, and accept or reject worker proposals. |
| `bb-lavender-haze` / `ctf-lavender-haze` | Reconnaissance and artifact mapping; seed harness coverage within explicit scope. |
| `bb-vigilante-shit` / `ctf-vigilante-shit` | Explicitly authorized hands-on hunting or challenge solving, with recorded evidence. |
| `bb-archer` | Explicitly scoped smart-contract / blockchain review and validation. |
| `bb-worker` / `ctf-worker` | Generic scoped worker execution for a single approved queue item. |
| `bb-blockchain-worker` | Worker execution for a scoped on-chain / contract task. |
| `bb-profiler` | Build and maintain reusable target-organization profile knowledge. |
| `ctf-overseer` | Oversee a multi-challenge CTF: intake, prioritization, and roll-up. |
| `karma` | Independent adversarial verifier: challenge evidence and readiness before promotion. |
| `mirrorball` | Post-engagement retrospective on process, template fit, and tooling. |
| `hub-architect` | Evolve the engine itself — templates, harness, and documentation. |
| `tools-curator` | Curate and wire the MCP tool source into an agent safely. |
| `clean` | Scrub internal terms and private detail from a draft before it leaves the workspace. |

The `_shared/` directory holds baseline instructions common to several roles
(for example a worker baseline) so individual skills stay short.

## Skill file format

Each role is a directory under `roles/<role>/` (surfaced at
`.claude/skills/<role>/` by the initializer) containing a `SKILL.md` with YAML
frontmatter and a short body. The stub below shows the shape the engine expects
— fill the body with your own operating instructions:

```markdown
---
name: bb-mastermind
description: One line describing when this role is invoked and what it owns.
---

# Title

Read `.claude/skills/_shared/WORKER-BASELINE.md` and the active engagement
rules first. State the role's authority, its inputs, its outputs, and its stop
conditions. Require evidence. Do not grant permission the operator does not
already have, and do not let one session choose scope, run hands-on work, and
approve its own result.
```

## Wiring the roles

The repository already ships a generic `roles/` folder. Run the initializer to
wire it to `.claude/skills/`, create the Codex `.agents/skills` symlink, and
enable the git hooks — without overwriting anything that already exists:

```sh
python3 scripts/harness/init_workspace.py --root .
```

Then edit each `roles/<role>/SKILL.md` to encode your playbook. Version those
filled-in files with your private operating setup, never in a public remote.
This repository ships the reusable engine and generic stubs; the instructions
you write behind each role remain yours.
