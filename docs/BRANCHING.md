# Branching and private engagements

Keep the reusable tool separate from real work.

```text
main (private)         framework + company profiles (profiles/<company>/)
  COMPANY (e.g. ACME) company branch -- diverges from main, holds engagement data
    engagement          engagement branch off company branch
      sub-finding       optional sub-branch off engagement
public-main            documentation-only export snapshot
```

## What lives where

| Branch | Contains | Never contains |
|---|---|---|
| `main` | Framework code, templates, harness scripts, MCP source, company profiles (`profiles/<company>/`), registry (`ENGAGEMENTS.md`), plans, internal docs | Engagement data: findings, scope, target config, evidence, PoC scripts, activity logs |
| Company branch | Everything from main at branch time + engagement-specific data | Nothing extra -- it diverges from main and is never fully merged back |
| Engagement branch | Full working state for one engagement | Hub-level plans (removed after branching) |
| `public-main` | Allowlisted documentation-only export | Anything private -- registry, plans, internal docs, profiles, engagement data |

## Merge direction

Full merges flow **up** the engagement chain only:

```text
sub-finding --> engagement --> company branch    (full merge OK)
company branch --> main                          (NEVER -- cherry-pick profiles/ commits only)
```

To bring a company profile to main, cherry-pick the specific `profiles/` commit.
Never run `git merge <company-branch>` into main -- that pulls engagement data
onto the framework branch.

## Hub architecture branches

Bulk framework changes use a tracked development branch named
`feat-<two-or-three-words>` or `patch-<two-or-three-words>`, such as
`feat-backpatch-compatibility`. Review and merge that branch into `main`
before backpatching engagement branches. The engagement guard recognizes this
name pattern and still warns about framework edits on ordinary engagement
branches.

## Engagement branch guard

A versioned `.githooks/pre-commit` hook blocks engagement-data paths on `main`.
A `.githooks/pre-merge-commit` hook blocks merges that would bring engagement
files onto main. Enable hooks once per clone:

```bash
git config core.hooksPath .githooks
```

Run `python3 scripts/engagement_guard.py preflight` before active engagement
work, and `python3 scripts/engagement_guard.py closeout` before closing one.

## Private vs. public separation

For a public fork, create private engagement branches locally or in a separate
private remote. Publish only the reusable-tool branch via the export script
(`scripts/export_public_docs.py`). Before any public push, review the exact
files being sent and confirm that no target identifiers, credentials, or
evidence are included.
