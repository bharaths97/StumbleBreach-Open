# Overview

This project is a reusable tool for AI-assisted security research,
capture-the-flag exercises, and other authorized technical reviews. It ships
with templates, deterministic harness scripts, MCP tool-server source, and
documentation for using Claude Code or Codex CLI responsibly.

The framework is deliberately neutral about targets and operators. A new
workspace is created from a template, then populated only with information
that is authorized for that workspace.

## Core ideas

- Keep scope explicit and confirm authorization before any testing.
- Separate planning and review from hands-on work -- the mastermind decides,
  the worker executes, and karma challenges before promotion.
- Record decisions, evidence, and progress in ordinary files.
- Use repeatable scripts for mechanical validation and duplicate detection.
- Keep private target data, credentials, and raw output outside the reusable
  tool repository. Company knowledge base profiles live in `profiles/<company>/`
  on the framework branch.

The public documentation describes the model. Templates and local instructions
provide the details needed for a particular authorized workspace.

## Documentation map

- [Engine and playbook](ENGINE-AND-PLAYBOOK.md) — what this repo ships versus
  the private role instructions that drive it, and how the two connect.
- [Architecture](ARCHITECTURE.md) — how templates, roles, tools, and the
  coverage harness fit together.
- [Harness](HARNESS.md) — the deterministic coverage and reporting scripts.
- [Roles](ROLES.md) — the planning, worker, and review separation.
- [Skills](SKILLS.md) — the role roster, skill file format, and stub generator.
- [Branching](BRANCHING.md) — a safe private-engagement branch model.
- [Tooling](TOOLING.md) — MCP source, local dependencies, and the doctor.
- [Workflow](WORKFLOW.md) — the lifecycle from intake through close-out.
- [Safety](SAFETY.md) — authorization, data handling, and review boundaries.
- [Security hardening](SECURITY-HARDENING.md) — planned safeguards for native tool execution and publication.
- [Extending](EXTENDING.md) — how to adapt templates and add safe automation.
- [Setup](SETUP.md) — generic Claude Code and Codex CLI setup.
