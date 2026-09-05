# Rules & Project Layout

The shared source of truth for this engagement — referenced by
`CLAUDE.md`, `AGENTS.md`, and the `/bb-mastermind`/`/bb-lavender-haze`/`/bb-vigilante-shit` skills.
Read this before doing any work, regardless of which session or
CLI is reading it. CLAUDE.md/AGENTS.md only hold what differs between
the two CLIs; everything else lives here so there's nothing to keep in
sync.

## Project

Authorized bug-bounty engagement: {{ENGAGEMENT_NAME}} —
{{TARGET_DESCRIPTION}}. Two roles, one continuous engagement (not
per-target sessions): **overseer** (plans, reviews, enforces
scope/guardrails, owns `findings/plan.md`, no exploitation tool access)
and **worker** (hands-on testing, tool access, owns raw evidence in
`logs/`). A recon worker is selected explicitly: `/bb-lavender-haze`; the hunting worker is `/bb-vigilante-shit` for web/API
work and `/bb-archer` for contract, fork, fuzz, invariant,
or static blockchain work. `/karma` is a project-local helper
role for adversarially checking flagged claims before promotion or
submission; it is not a worker or final signoff role. Roles are Claude
Code skills local to the
`StumbleBreach` project root's `.claude/skills/` — not
tracked in this repo, and not global. A role's duties don't change
between engagements, only the target does. This project holds data
(scope, findings, evidence) and permissions; the skills hold "how to
act."

## Layout

- `scope.md` — authorization + target scope, the source of truth for
  what's in play. Filled in by the human before any testing begins.
  Sessions may append to its "Notes / open questions" section; nothing
  else in it changes without explicit human confirmation (see
  permissions).
- `references/` — optional: methodology/payload repos relevant to this
  target, pulled via `setup-resources.sh` if used. Read-only, not
  edited, not committed (git-ignored — can be large).
- `logs/agent-scan-logs/`, `logs/network-captures/` — raw evidence.
  Owned by the worker role. Git-ignored — scratch space, not the
  deliverable. (Rename/repurpose these two folders if this engagement's
  evidence doesn't fit an "agent scan logs + packet captures" shape —
  the split that matters is raw-and-ignored vs. curated-and-tracked,
  not these exact folder names.)
- `logs/activity.log` — engagement-wide "who ran what, when" audit
  trail, separate from the raw evidence above. Tracked in git. See
  "Activity logging" below.
- `findings/plan.md` — running test plan + status, owned by the
  overseer role.
- `findings/JOURNEY.md` — session-by-session narrative of decisions,
  pivots, and outcomes. Captures the reasoning behind direction changes.
- `findings/TEMPLATE-finding.md` — template for a candidate finding.
- `findings/<finding-slug>.md` — one file per candidate finding, created
  only after overseer sign-off (see rule below).
- `findings/evidence/<finding-slug>/` — curated proof for a specific
  finding (screenshots, decompiled snippets, extracted config, trimmed
  log excerpts) referenced from that finding's write-up. Tracked in git
  — this is the deliverable evidence, distinct from the raw bulk logs
  in `logs/`.
- `config/target.env(.example)` — real target IPs/build numbers and the
  machine-enforced web/blockchain scope fields. `target.env` is git-ignored,
  filled in by the human.
- `tools/` — one-time environment setup notes, per box/environment if
  more than one is involved.
- `harness/coverage.json` — persistent area-by-attack-class coverage
  state. Read this at session start instead of reconstructing coverage
  from every finding and log.
- `harness/queue.md` — overseer-proposed hunt tasks. Workers only take
  post-Gapfill work whose queue row is explicitly `selected` by the
  human (or overseer under the user's explicit instruction).
- `harness/adapters/` — domain taxonomy, recon procedure, tool bindings,
  and finding-schema extensions for web, blockchain, and binary work.
- `scripts/harness/` — shared deterministic coverage seeding, schema
  validation, duplicate shortlisting, and report generation helpers.
- `harness/report.md` — generated, git-ignored orientation report;
  regenerate it on demand rather than maintaining it by hand.

## Which role is this session?

Determined by which skill was invoked to start it — `/bb-mastermind`, `/bb-lavender-haze`,
`/bb-vigilante-shit`, or `/bb-archer` — not a file to read. The
overseer selects a web worker for web/API-only plan items, a blockchain
worker for contract-only plan items, and separate sessions for mixed
scope. If it is not obvious which role this session should be, ask the
user before doing anything else.

## Hard rules

1. **Scope.** Nothing proceeds until `scope.md` has no remaining
   placeholders in Target/Authorization/In-scope. Nothing outside what
   `scope.md` lists as in-scope is touched, ever — if a target, host, or
   action isn't explicitly listed, stop and ask.

2. **Guardrail.** No action that installs, uninstalls, patches, deploys a
   configuration, or otherwise modifies a target system without explicit
   human confirmation first. Read-only recon, log inspection, static
   binary analysis, and traffic capture don't need per-action
   confirmation, but still get logged (rule 5).

3. **Findings go through the overseer.** The worker proposes a candidate
   finding informally first (chat/notes); only after the overseer
   sanity-checks it does `findings/<finding-slug>.md` get created from
   `findings/TEMPLATE-finding.md`. Don't skip straight to a findings file.

4. **Prior-art check.** Before treating anything as a novel finding,
   search Exploit-DB, NVD/CVE, and GitHub Security Advisories for the
   exact target version in `scope.md`. Record the result in that
   finding's "Prior-art check" section. A bug already reported against
   this version isn't a new finding.

5. **Activity logging.** Every session appends one line to
   `logs/activity.log` for each tool run, install/analysis step, or
   user-confirmed action — a chronological "who ran what" audit trail,
   separate from the raw evidence in `logs/` and from the findings
   themselves. Format: `<ISO8601 timestamp> [<actor>/<role>] <action>`,
   where actor is `user`, `claude`, or `codex`, and role is `overseer`
   or `worker`. Log the action whether it was the session's own tool
   call or a command the user ran and confirmed back.

6. **Evidence handling.** Sessions don't take or save screenshots
   themselves — the user captures them and saves to
   `findings/evidence/<finding-slug>/`, tells the session the filename,
   and the session references it from the finding write-up. Same
   principle as raw tool output: give the user the exact command/action,
   let them confirm back, then log it.

7. **No fabrication.** Never invent scan results, log contents, packet
   captures, or findings. If something wasn't actually run/observed, say
   so plainly.

8. **Submission cross-check.** Before anything goes to the program,
   verify the finding is (a) in scope per `scope.md`, (b) not a
   known/duplicate issue per the prior-art check, (c) has reproducible
   steps, and (d) has evidence attached — the "Overseer sign-off"
   checklist in the finding file itself. If the user, overseer, worker,
   model baseline, duplicate risk, scope sensitivity, or evidence gap
   flags a candidate for adversarial review, run it through
   `/karma` before treating it as promotion/submission-ready.

9. **Git discipline.** Small, frequent commits as work happens — don't
   batch a full day's testing into one commit. Branch off this
   engagement's branch for a body of work that would otherwise leave it
   half-done for a while (see the hub's own `RULES.md` for the naming
   convention), and merge back when checkpointed.

10. **Live research is expected.** Both roles are expected to use web
    search/fetch for CVE, NVD, Exploit-DB, and advisory lookups against
    the exact target version in `scope.md` — that's how prior-art checks
    (rule 4) and the overseer's "is this already known/patched" review
    get done. Don't use it for anything beyond that.

11. **Blockchain scope gates.** Blockchain work requires
    `TARGET_SURFACES` to include `blockchain` plus an explicit in-scope
    contract, repository, chain ID, or RPC endpoint for the requested task.
    Scope flags, not a worker's current skill, decide whether fuzzing,
    invariants, local-fork mutation, or any transaction-capable action is
    allowed. Mainnet/testnet transactions always require a fresh, exact human
    confirmation in addition to the corresponding true scope flag.

12. **Scope expansion requires scope.md update.** Before planning work
    outside the original in-scope list -- new attack surfaces, escalation
    targets, or pivots to different components -- update scope.md's
    "Notes / open questions" section or add a new "In scope" item with
    the authorization record. Plan files are not a substitute for scope
    authorization.

13. **Role awareness.** The overseer (mastermind) should delegate
    hands-on work (scans, compilation, PoC execution) to a worker
    session. If the user authorizes the overseer to take charge and
    execute directly, log the override in the activity log as
    `[actor/overseer+worker]` so the retrospective can distinguish
    deliberate hybrid operation from accidental role collapse. The
    worker MUST NOT sign off its own findings or expand scope. Karma
    should be invoked as a separate session when possible; if run
    inline, note it in the activity log.

14. **Evidence curation.** Before proposing a finding for sign-off, the
    worker copies deliverable evidence from `logs/` (scratch) to
    `findings/evidence/<finding-slug>/` (tracked). Finding write-ups
    reference curated evidence paths, not raw log paths.

16. **Principal verification.** Any finding whose root cause is a
    filesystem ACL, registry ACL, or permission misconfiguration MUST
    be reproduced with a purpose-built test account that represents the
    claimed attacker principal (e.g., a fresh Users-group-only local
    account for "low-privilege local user" claims). Evidence showing
    access as the installing user, an administrator, or SYSTEM does NOT
    satisfy the "low-privilege" claim. The test account name, group
    memberships, and `whoami /groups` (Windows) or `id` (macOS/Linux)
    output must be in the evidence file.

15. **Submission hygiene.** Any file intended for external submission
    (finding drafts, evidence files, report text) must contain zero
    internal project terminology. Scrub before finalizing:
    - Signal IDs (SIG-xxx), plan item IDs (P1.1, W46, M38, etc.)
    - Status tags (HUNTED, STAND, HOLD, REFUTED, karma, PROCEED, DROP)
    - Worker/role names (bb-lavender-haze, bb-vigilante-shit, bb-mastermind,
      bb-archer, bb-overseer, sub-overseer, worker delegation)
    - Stream tags (WIN, WEB, MAC) used as internal labels
    - Internal file references (orchestrator.md, plan.md, signals.md,
      coordinator tracker, harness/, queue.md, coverage.json)
    - Internal log paths (logs/webserver/worker-*, logs/mac-agent/*)
    The report must read as if written by a solo researcher submitting
    to a vendor bug bounty portal. No project scaffolding visible.
    Reference evidence as "see attached" not by internal repo path.
# Handoff records

Production handoffs live at `handoffs/<handoff_id>.json`, one JSON object per
file. Validate them from the engagement root with
`python3 scripts/validate_handoff.py handoffs/`; append the matching handoff
audit line to `logs/activity.log`.
