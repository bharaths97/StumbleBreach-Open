# Adapter: system

## Taxonomy seed

- sandbox-policy-bypass
- access-control-design-flaw
- privilege-boundary-analysis
- entitlement-misconfiguration
- os-configuration-audit
- escalation-chain
- path-vs-object-resolution
- policy-enforcement-gap

## Recon procedure

Enumerate sandbox profiles, entitlements, access control policies, and
privilege boundaries on the target system. Each distinct policy enforcement
mechanism or privilege boundary becomes an area. Use read-only enumeration
only and follow the engagement guardrails.

## Tool bindings

Use `binrev` MCP tools for static analysis of policy enforcement code.
Use system-native tools (sandbox-exec, codesign, security, sqlite3) for
local validation. Dynamic testing and target-modifying actions (installing
LaunchDaemons, modifying policy databases) require explicit human
confirmation per RULES.md rule 2.

## Finding schema extensions

Record the policy mechanism, enforcement layer (kernel/userspace), affected
profiles or entitlements, and whether confirmation is static or dynamic.

## Recommended external skills

- `tob-c-review`
- `tob-rust-review`
