---
slug: <finding-slug>
area: <area-id>
attack_class: <attack-class>
domain: <web, binary, blockchain, or system>
severity: <critical, high, medium, low, or informational>
status: draft
discovered_by: <worker/session identifier>
reviewed_by: <overseer/session identifier>
reviewer_role: overseer
reviewed_at: <ISO8601 UTC>
queue_ref: <area / attack-class>
endpoint: <URL or endpoint group>
method: <HTTP method>
parameter: <parameter or N/A>
auth_state: <unauthenticated, user, admin, or N/A>
contract_address: <contract address or N/A>
chain_id: <chain ID or N/A>
repo_commit: <repository and commit or N/A>
poc_environment: <static, local-fork, testnet, live-chain, or N/A>
function: <function name/address or N/A>
binary_build: <binary and build/version or N/A>
confirmation: <static, dynamically-confirmed, or N/A>
---

# Finding: <short title>

- **Status:** draft / under review / confirmed / submitted / duplicate / rejected
- **Date found:** <date>
- **Component:** <e.g. web console, REST API, agent, binary>
- **Version tested:** <from scope.md>
- **Discovered by:** overseer / worker (note which agent session)

## Summary

One or two sentences: what's wrong and why it matters.

## Vulnerability class

<e.g. insecure temp file, log injection, IDOR, missing auth check,
DLL hijack, hardcoded credential, insecure deserialization, etc.>

## Reproduction steps

1.
2.
3.

## Evidence

- Raw source (bulk logs, not committed): `logs/...`
- Curated proof for this finding (tracked, lives alongside this file):
  `findings/evidence/<finding-slug>/...` — screenshots, decompiled
  snippets, trimmed log excerpts. The user captures screenshots and
  tells the session the filename; sessions don't take or save them
  (RULES.md rule 6).

## Impact

What an attacker could actually do with this, and under what
preconditions (local access required? network position? auth level?).

## Prior-art check

- Exploit-DB search performed: yes/no — result:
- NVD/CVE search performed: yes/no — result:
- GitHub Security Advisories checked: yes/no — result:

## Overseer sign-off

- [ ] In scope per scope.md
- [ ] Not a known/duplicate issue
- [ ] Reproducible steps confirmed
- [ ] Evidence attached
- [ ] Ready to submit to <program's disclosure contact/portal>

## Readiness Gate

Before promotion to `confirmed` or `submitted`, create the curated-evidence
manifest with `python3 scripts/harness/validate_readiness.py
findings/<finding-slug>.md --write-manifest`, then run the command again
without that flag. Record the review in `logs/activity.log` as:
`<timestamp> [<actor>/overseer] finding=<finding-slug>
reviewer=<reviewed_by> decision=<confirmed-or-submitted-status>`.
