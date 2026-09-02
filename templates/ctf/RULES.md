# Rules & Project Layout

The shared source of truth for this project — referenced by CLAUDE.md,
AGENTS.md, and the `ctf-mastermind`/`ctf-lavender-haze`/`ctf-vigilante-shit` Claude Code skills. Read
this before doing any work, regardless of which session or CLI is
reading it. CLAUDE.md/AGENTS.md only hold what differs between the two
CLIs; everything else lives here so there's nothing to keep in sync.

## Project

Solo participant working {{ENGAGEMENT_NAME}}: {{TARGET_DESCRIPTION}}.
Work happens across multiple terminal sessions of Claude Code and/or
Codex CLI, coordinating entirely through files in this repo — there is
no shared memory between sessions, so the filesystem *is* the
coordination layer. Roles (overseer, worker) are Claude Code skills
local to the `StumbleBreach` project root's `.claude/skills/`
(`/ctf-mastermind`, `/ctf-lavender-haze`, `/ctf-vigilante-shit`) — not tracked in this repo, and not
global either. A role's duties don't change between competitions, only
the challenges do. This project holds data (challenges, findings,
status) and permissions; the skills hold "how to act." `/karma`
is a project-local helper role for adversarially checking flagged
challenge claims, exploit paths, flags, or report drafts before the
overseer treats them as submission-ready.

## Layout

- `challenges/intake/` — raw challenge description files, dropped in by
  the user, plus `general-rules.md` (the competition's rules, applies to
  every challenge). Read-only reference material; sessions don't edit
  these.
- `challenges/<name>/` — one folder per challenge, created as challenges
  appear in intake, each with `planning.md`, `instructions.md`,
  `notes.md`, `STATUS.md`, `activity.log`, a `results/` folder for raw
  tool output (git-ignored — scratch space, not the deliverable), and a
  `report/` folder for the submission write-up + evidence (tracked — see
  "Reporting" below).
- `STATUS.md` (root) — rollup across all challenges, owned only by the
  overseer session.
- `skill-library/` — full vendor skill repos, **not** auto-loaded, never
  copied anywhere else. A lookup shelf; check `skill-library/INDEX.md`
  before assuming something isn't available, then read the specific
  file needed. See `skill-library/README.md`. Optional — only relevant
  if this competition benefits from pulling in external skill repos.
- `planning/overview.md` — cross-challenge strategy and priorities.
- `tools/environment-check.md` — running list of what tools are needed
  and confirmed installed.

## Which role is this session?

Determined by which skill was invoked to start it:

- **Overseer session** (the main long-running terminal): invoke
  `/ctf-mastermind`.
- **Recon session** (scoped to one challenge): invoke `/ctf-lavender-haze` to map issued artifacts and environment.
- **Worker session** (scoped to one challenge): invoke `/ctf-vigilante-shit` —
  it reads `challenges/<name>/instructions.md` first (written by the
  overseer) for this session's specific target scope.

If it's not obvious which role this session should be, ask the user
before doing anything else, and tell them which skill to invoke.

## Hard rules

These are non-negotiable regardless of which session or CLI is reading
this.

1. **Scope.** This project only covers the challenges issued for this
   competition, described in `challenges/intake/`. Nothing outside
   those targets/scopes is in play. Each challenge's `planning.md`
   records its exact in-scope target(s) (host/IP/port/hosts-file entry)
   under `## Scope` — pulled from that challenge's intake file. If a
   target isn't listed there, don't touch it.

2. **No silent tool execution assumptions.** Never assume a tool is
   installed. Check `tools/environment-check.md` first; if a tool's
   status is unconfirmed, give the user the command to verify it rather
   than assuming.

3. **No auto-piping of output.** Sessions do not execute commands that
   pipe output directly into files on the user's behalf. Give the user
   the exact command (including `tee`/redirect target) and let them run
   it. This keeps a clean, deliberate audit trail of what was actually
   run.

4. **Folder scope per session type.**
   - The overseer session may read/write anywhere under `challenges/`,
     `STATUS.md`, `planning/`, `tools/`.
   - A worker session scoped to one challenge only reads/writes inside
     `challenges/<name>/`. It does not edit root `STATUS.md`, other
     challenges' folders, or shared docs (CLAUDE.md, AGENTS.md,
     RULES.md, REPORT_TEMPLATE.md).
   - If a worker session believes it needs to touch something outside
     its scope, it stops and tells the user rather than doing it.

5. **Status logging.** Any session working inside `challenges/<name>/`
   updates that challenge's own `STATUS.md` as work happens. Only the
   overseer session aggregates those into the root `STATUS.md`.

6. **No fabrication.** Never invent scan results, flag values, tool
   output, or findings. If something wasn't actually run/observed, say
   so plainly.

7. **Git discipline.** Small, frequent commits. Message format:
   `<challenge>: <short description>` for challenge-branch work, or a
   plain description for engagement-branch shared-doc changes. Root
   `STATUS.md` is only ever committed on the engagement branch, only by
   the overseer.

8. **Session hygiene.** Proactively suggest starting a new session when:
   switching challenge focus, task type changing (recon → exploitation
   → write-up), or context is visibly overloaded/cluttered.

9. **Skill gaps.** If nothing in `skill-library/` covers something a
   challenge needs, say so in that challenge's `notes.md` rather than
   improvising undocumented one-off methodology silently.

10. **Skill library usage.** If `skill-library/` is populated for this
    competition: check `skill-library/INDEX.md` (cheap to read in
    full), tell the user what you found and how you intend to use it,
    then read just the specific file needed for the current task —
    every time it's relevant, not a one-time promotion. Never bulk-read
    or dump a whole vendor repo into context.

11. **Activity logging.** Every session appends one line to
    `challenges/<name>/activity.log` for each tool invocation or
    user-confirmed action taken within that challenge — a chronological
    "who ran what" audit trail, separate from `notes.md` (findings) and
    `STATUS.md` (current state). Format:
    `<ISO8601 timestamp> [<actor>/<role>] <action>`, where actor is
    `user`, `claude`, or `codex`, and role is `overseer` or `worker`.
    Log the action whether it was the session's own tool call or a
    command the user ran and confirmed back.

12. **Competition rules.** `challenges/intake/general-rules.md` holds
    this competition's rules — read it once before starting work on any
    challenge, alongside this file. Translate its restrictions into
    session behavior (typically: no brute force against login/flag
    submission, no high-volume/automated scanning unless explicitly
    allowed, no DoS, attack only the intended vulnerability surface —
    never the platform/scoreboard itself, no seeking hints, flags
    reported exactly as found).

13. **Reporting.** Once a challenge's flag(s) are captured (or the user
    asks for a write-up regardless of status), draft
    `challenges/<name>/report/report.md` from `REPORT_TEMPLATE.md` at
    the project root, filled in from that challenge's `notes.md`,
    `activity.log`, and `planning.md`. `challenges/<name>/report/` is
    tracked in git — the curated submission deliverable, distinct from
    `results/` (raw tool output, git-ignored scratch space). Screenshot
    evidence goes in `challenges/<name>/report/evidence/`: sessions
    don't take or save screenshots themselves, the user saves the
    screenshot and tells the session the filename, and the session
    references it from `report.md`. The user reviews and edits
    `report.md` before actually submitting it — a session drafts it, it
    doesn't submit anything.

14. **Adversarial verification.** If the user, overseer, worker,
    contradictory records, evidence gaps, or report uncertainty flag a
    challenge claim for adversarial review, run it through
    `/karma` before treating the claim or write-up as
    submission-ready. The verifier is read-only by default and reports
    back to the overseer; it does not submit, run worker tools, or
    replace final overseer judgment.
