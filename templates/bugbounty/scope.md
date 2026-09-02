# Scope

Fill this in before any testing begins. Both roles should treat this file
as the source of truth for what's authorized.

## Target

- Product/system: {{TARGET_DESCRIPTION}}
- Version/build number: <fill in>
- Host(s)/IP(s): <fill in>
- Entry point (console URL, API base, etc.): <fill in>

## Authorization

- Program name/reference: <fill in — e.g. a bug bounty platform program
  page, a signed engagement letter, an explicit CTF program's rules>
- Program scope/terms snapshot: <paste or link the relevant section here>
- Testing window: <fixed window if the program specifies one, else "no
  fixed window">

## In scope

- <list explicitly what's authorized — systems, protocols, components>

## Blockchain / smart contract scope

Complete this optional section for blockchain/smart-contract engagements.
Machine-enforced values belong in `config/target.env`; keep the two
records consistent.

- Ecosystem/VM: <EVM / Solana / Substrate / other>
- Chain/network(s): <Ethereum mainnet, Sepolia, local fork, etc.>
- Chain ID(s): <fill in>
- Contract address(es): <exact addresses, if deployed>
- Source repo / commit: <repo URL/path + commit hash>
- Proxy/admin contracts: <fill in>
- Token/NFT contracts: <fill in>
- Oracle dependencies: <fill in>
- Bridge/cross-chain components: <fill in>
- Governance/DAO components: <fill in>
- Off-chain services/indexers/keepers: <fill in>
- Frontend/API/RPC endpoints: <fill in>
- Allowed testing methods: <static review, local fork PoCs, fuzzing, invariant tests, read-only on-chain analysis>
- Allowed transaction behavior: <mainnet/testnet/local fork rules>
- Gas/spend budget: <fill in>
- Explicit blockchain exclusions: <live market manipulation, MEV, DoS/gas griefing, third-party protocols, private keys, social engineering>

## Explicitly out of scope

- Anything not named above
- Any host on the network other than what's named above
- Anything that would affect production infrastructure not part of this
  target
- Denial-of-service testing unless the program explicitly allows it —
  assume not allowed until confirmed
- Social engineering, physical access, third-party dependencies not
  bundled with the target, unless explicitly in scope

## Notes / open questions

- <log anything ambiguous here for the overseer to flag before the
  worker proceeds>
