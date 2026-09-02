# Adapter: web

## Taxonomy seed

- authn/authz
- injection
- SSRF
- IDOR
- deserialization
- business-logic
- misconfig
- info-disclosure
- rate-limit-DoS-adjacent

## Recon procedure

Use the `recon` and `webapp` MCP tools against `IN_SCOPE_WEB_TARGETS` or
`IN_SCOPE_TARGETS`. Each distinct host or endpoint group becomes an area.
Use non-destructive discovery only and follow the engagement guardrails.

## Tool bindings

Use `webapp` tools such as nuclei, sqlmap, ffuf, dalfox, arjun, commix,
nikto, and wpscan, plus manual testing, only when they are in scope and
authorized.

## Finding schema extensions

Record endpoint, method, parameter, and required authentication state.

## Recommended external skills

Consult these registry identifiers only when they match the selected
cell; they are on-demand references, not installed CLI skills:

- `tob-static-analysis`
- `tob-audit-context-building`
- `tob-variant-analysis`
- `tob-supply-chain-risk-auditor`
- `tob-semgrep-rule-creator`
