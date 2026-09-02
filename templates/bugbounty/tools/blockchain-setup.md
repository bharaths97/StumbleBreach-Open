# Blockchain / smart-contract setup

Use this note only after `scope.md` and `config/target.env` explicitly name a
blockchain surface. Installed tools and cloned repositories are local state,
not template content or evidence.

## Local analysis toolchain

- Node/npm plus a project-local Hardhat dependency. Run Hardhat through
  `npx --no-install hardhat test`; do not let a wrapper download packages.
- Foundry/Forge for unit tests, fuzzing, and invariants.
- Slither for static analysis.
- Echidna for property fuzzing.
- Mythril is optional and can be slower/noisier; record its version if used.
- `sol2uml` is optional for local source-structure visualisation.

Record the command and version for every tool actually used in
`logs/activity.log`. Installation or upgrades change the local analysis
machine and require explicit human confirmation under `RULES.md`.

## RPC and secret hygiene

- Put RPC URLs, provider tokens, and wallet configuration in ignored local
  environment files only. Never commit them, paste them into logs, or pass
  private keys, seed phrases, or wallet secrets to an agent or MCP tool.
- Prefer a local node or fork. A fork must use only the chain/RPC/block range
  declared in `config/target.env`.
- Read-only RPC calls are not permission to submit a transaction. Mainnet and
  testnet transactions require both a true scope flag and a fresh, exact human
  confirmation; local-fork mutations require their own scope flag.
- Keep gas/spend limits in `MAX_TESTNET_GAS_ETH` and stop if the permitted
  transaction behavior is ambiguous.

## Safe operating modes

Start with static review and local tests. Run fuzzing only when
`ALLOW_FUZZING=true`, and invariants only when
`ALLOW_INVARIANT_TESTING=true`. Never use local tooling for live MEV, oracle
manipulation, DoS, gas griefing, market manipulation, or third-party protocol
testing unless the exact action is explicitly authorized in scope.
