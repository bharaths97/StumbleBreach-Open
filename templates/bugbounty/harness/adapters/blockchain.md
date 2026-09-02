# Adapter: blockchain

## Taxonomy seed

- reentrancy
- access-control
- arithmetic-precision
- tx-origin
- unchecked-returns
- replay-signature
- DAO-governance
- DEX-AMM-logic
- flash-loans
- oracle-manipulation
- frontrunning-MEV
- vault-strategy-logic
- DoS-gas-griefing
- sensitive-on-chain-data

## Recon procedure

Perform static repository review and `slither_scan`; each contract or
module becomes an area. This adapter takes effect only when
`TARGET_SURFACES` includes `blockchain` and the blockchain-plan tooling
is available.

## Tool bindings

Use `forge_test`, `forge_fuzz`, `echidna_fuzz`, and `mythril_analyze`
only through blockchain scope enforcement. Never auto-execute a
transaction.

## Finding schema extensions

Record contract address, chain ID, repository/commit, and whether the
PoC ran as static analysis, a local fork, a testnet action, or a
live-chain action.

## Recommended external skills

Consult these registry identifiers only when they match the selected
cell; they are on-demand references, not installed CLI skills:

- `tob-building-secure-contracts`
- `tob-audit-context-building`
- `tob-supply-chain-risk-auditor`
- `tob-static-analysis`
- `tob-differential-review`
- `tob-rust-review`
