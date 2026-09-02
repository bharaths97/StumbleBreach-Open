# External methodology registry

The identifiers below are lookup keys for the ignored vendor cache, not
Claude or Codex skills. Read a matching source file only for the current
authorized harness cell. Source snapshot: Trail of Bits `skills` at
`e6066e7db1fd57cb35f9a534781ceec595327feb`.

| Reference | Source path (under `vendor/tob/`) | Category | Domain(s) | Stage(s) | Attack class(es) | Executes tools? | Notes |
|---|---|---|---|---|---|---|---|
| `tob-static-analysis` | `plugins/static-analysis/skills/{codeql,semgrep,sarif-parsing}/SKILL.md` | static analysis | web, blockchain, binary | hunt | broad code flaws | Yes; scans require confirmation | Pick CodeQL, Semgrep, or SARIF parsing as appropriate; the source plugin is split into these three files. |
| `tob-building-secure-contracts` | `plugins/building-secure-contracts/skills/{algorand-vulnerability-scanner,cairo-vulnerability-scanner,cosmos-vulnerability-scanner,solana-vulnerability-scanner,substrate-vulnerability-scanner,ton-vulnerability-scanner}/SKILL.md` | contract review | blockchain | recon, hunt | chain-specific contract flaws | Yes; may scan local source | Choose only the scanner matching the declared ecosystem. |
| `tob-audit-context-building` | `plugins/audit-context-building/skills/audit-context-building/SKILL.md` | codebase understanding | web, blockchain, binary | recon | unfamiliar codebase | Yes; creates analysis artifacts and may parallelize | Use first for an unfamiliar in-scope repository. |
| `tob-supply-chain-risk-auditor` | `plugins/supply-chain-risk-auditor/skills/supply-chain-risk-auditor/SKILL.md` | dependency risk | web, blockchain | recon | dependency, abandonment, publisher concentration | Yes; read-only analysis | Covers npm, PyPI, and Go ecosystem risk. |
| `tob-variant-analysis` | `plugins/variant-analysis/skills/variant-analysis/SKILL.md` | pattern expansion | web, blockchain, binary | hunt | known bug variants | Yes; may parallelize | Use after a concrete bug pattern is established. |
| `tob-differential-review` | `plugins/differential-review/skills/differential-review/SKILL.md` | change review | web, blockchain | recon, hunt | security-relevant changes | Yes; reads Git history | Use for an actively updated in-scope repository. |
| `tob-c-review` | `plugins/c-review/skills/c-review/SKILL.md` | C/C++ review | binary | hunt | memory safety, C/C++ logic | Yes; scripts and parallel agents | Requires explicit confirmation before tool or subagent execution. |
| `tob-rust-review` | `plugins/rust-review/skills/rust-review/SKILL.md` | Rust review | binary, blockchain | hunt | unsafe, FFI, async, concurrency | Yes; scripts and parallel agents | Requires explicit confirmation before tool or subagent execution. |
| `tob-semgrep-rule-creator` | `plugins/semgrep-rule-creator/skills/semgrep-rule-creator/SKILL.md` | custom detection | web, blockchain, binary | hunt | repeating code pattern | Yes; writes/runs rules | Use only once a pattern merits reusable detection. |
| `tob-fp-check` | `plugins/fp-check/skills/fp-check/SKILL.md` | false-positive review | any | validate | candidate finding | No target tooling | Apply before proposing a candidate finding. |
| `tob-vulnerability-triage-brocards` | `plugins/vulnerability-triage-brocards/skills/vulnerability-triage-brocards/SKILL.md` | report triage | any | validate | candidate finding | No target tooling | Use its judgement criteria to accept, dismiss, or request detail. |
| `tob-constant-time-analysis` | `plugins/constant-time-analysis/skills/constant-time-analysis/SKILL.md` | timing side channels | binary | hunt | crypto timing | Yes; local analysis | Crypto-code only. |
| `tob-zeroize-audit` | `plugins/zeroize-audit/skills/zeroize-audit/SKILL.md` | secret zeroization | binary | hunt | missing or optimized-away wipes | Yes; scripts and parallel agents | Requires explicit confirmation before tool or subagent execution. |
| `tob-dwarf-expert` | `plugins/dwarf-expert/skills/dwarf-expert/SKILL.md` | DWARF analysis | binary | recon, hunt | debug-info inspection | Yes; read-only local tools | Pair with the existing `binrev` MCP tools where relevant. |
