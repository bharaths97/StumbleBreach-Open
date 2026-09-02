# Report Template

Copied to `challenges/<name>/report/report.md` once a challenge's flag(s)
are captured, or whenever the user asks for a write-up. Fill it in from
that challenge's `notes.md`, `activity.log`, and `planning.md` — this is
the polished, submittable version; those are working documents. See
`RULES.md` #13.

The user reviews and edits this before submitting anything — a session
drafts it, it doesn't submit it.

---

## Challenge

**Name:** <challenge-name>
**Points:** <points value, from the intake file>
**Category:** <web / AI-ML / etc.>

## Summary

<one paragraph: what the vulnerability was and how it was exploited, in
plain terms someone unfamiliar with the challenge could follow>

## Target / scope

<host, port, URL — copied from planning.md's Scope section>

## Vulnerability class

<e.g. IDOR, SSRF, SQL injection, prompt injection, auth bypass>

## Steps to reproduce

1. <first step>
2. <next step>
3. ...

Reference evidence inline where it helps, e.g.
`See evidence/01-initial-request.png`.

## Flags

| Label | Value | Captured (date, UTC) |
|---|---|---|
| flag1 | | |

## Evidence

List each file in `challenges/<name>/report/evidence/` with a one-line
description of what it shows. The user saves screenshots there —
sessions don't capture or save evidence themselves (RULES.md #13).

- `evidence/<filename>` — <what it shows>

## Notes

<anything unusual worth flagging to a reviewer — red herrings, alternate
paths, things that didn't work and why>
