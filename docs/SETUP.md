# Setup with Claude Code or Codex CLI

Follow the current official documentation for each CLI's installation,
authentication, and account requirements. This repository provides the
reusable workflow and source; it does not ship credentials, target access, or
preinstalled scanning tools.

## Prepare a workspace

1. Clone or copy this repository into a directory you control.
2. Enable the versioned git hooks: `git config core.hooksPath .githooks`
3. Bootstrap the playbook skeleton (create-only, never overwrites):
   `python3 scripts/harness/init_workspace.py --root .` — this lays down the
   `.claude/skills/` role stubs and the Codex `.agents/skills` symlink for you
   to fill in. See [Skills](SKILLS.md) and
   [Engine and playbook](ENGINE-AND-PLAYBOOK.md).
4. Read the root project rules and the public documentation.
5. Choose an appropriate template and create a private working branch.
   For bug-bounty engagements, optionally create a company branch first
   (e.g. `ACME`) to hold reusable target knowledge in `profiles/<company>/`.
6. Fill in scope, authorization, and deliverable metadata using placeholders
   until the owner approves the real values.
7. Keep credentials, raw evidence, and private configuration in the private
   engagement branch or your approved secret store, never in a public remote.

## Reusable scripts and tool source

- `scripts/ctf_scaffold.py` creates and rolls up CTF challenge records.
- `scripts/bb_scaffold.py` initializes the selected bug-bounty adapters and
  coverage areas after an engagement branch is created from the template. It
  keeps using the shared harness scripts; it does not create a branch or add
  an engagement to any registry. For example:

  ```sh
  python3 scripts/bb_scaffold.py --root . --surface web \
    --area web:login-api="authenticated login API"
  ```
- `scripts/harness/` seeds coverage, validates finding structure, identifies
  likely duplicates, and renders a report for a bug-bounty engagement.
- `tools_mcp/` contains source for the `recon`, `webapp`, and `blockchain` MCP
  registries and their scope guard. See [Tooling](TOOLING.md) before wiring it
  into an agent.

Create the local tool environment when you want to use the MCP source:

```sh
python3 -m venv tools-env/.venv
```

Install the compatible MCP and `unified_agent` runtime required by your chosen
agent setup, then run `tools_mcp/doctor.py`. The doctor reports missing Python
packages, command-line tools, wordlists, and optional GUI-hosted integrations
rather than assuming a particular operating system or package manager.

## Claude Code

Start Claude Code from the repository root. Ask the session to read the
project rules and identify its role before doing work. Invoke the applicable
project skill or provide equivalent role instructions. A planning session
should create and review a plan; a worker session should operate only on an
approved work item; a reviewer should challenge evidence and conclusions.

## Codex CLI

Start Codex CLI from the same repository root. Let it discover the repository's
agent instructions, then ask it to read the rules and identify its role. Use
the same role boundaries and file-backed handoffs as Claude Code. If a newly
added instruction or skill is not discovered, restart the CLI and verify that
the session is in the repository root.

## First run checklist

- Confirm the current branch or working copy is the intended one.
- Confirm authorization and scope before any network interaction.
- Confirm the role and its allowed actions.
- Run `python3 scripts/engagement_guard.py preflight` on the engagement branch.
- Run read-only validation or tests appropriate to the template.
- Review the diff before committing or sharing anything.

Agents may create local commits for explicitly authorized changes, but must
never push to a remote. Publication or remote updates remain an explicit
human-controlled step after reviewing the exact export.

Never merge an engagement or company branch into main. To bring company profile
data to main, cherry-pick the specific `profiles/` commit and verify with
`git diff --name-only main~1..main`.

The framework does not provide credentials, target access, or permission to
perform testing. Those must be supplied and approved separately by the owner.
