# Extending the framework

The safest extension is a small, deterministic change that preserves the
workflow's scope and review gates.

## Templates

Add or refine a template when a pattern will be reused across many authorized
workspaces. Use placeholder values for names, targets, dates, and identifiers;
never bake real engagement data into a template.

## Roles and instructions

Role instructions should state their authority, inputs, outputs, and stop
conditions. Keep planning, hands-on work, and review responsibilities distinct.
Instructions should require evidence and should not grant permission that the
operator does not already have.

## Automation

Prefer scripts that validate structure, normalize records, calculate coverage,
or identify duplicates without making network changes. Add tests for malformed
input and unexpected state. Document whether a script is read-only, local-only,
or capable of external effects.

## Contributions

Before contributing, check the public-data boundary, run the relevant tests,
and inspect the diff for secrets, personal information, target identifiers,
local paths, and generated artifacts. Keep operational notes in a private
location rather than in the public documentation tree.
