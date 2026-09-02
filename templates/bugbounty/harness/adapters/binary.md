# Adapter: binary

## Taxonomy seed

- memory-corruption
- integer-overflow-underflow
- format-string
- type-confusion
- race-condition-TOCTOU
- unsafe-deserialization
- logic-auth-bypass
- hardcoded-secrets-keys
- unsafe-library-calls
- missing-bounds-checks

## Recon procedure

Use `list_functions`, `list_imports`, and `list_exports` to map exported,
entry, and attacker-reachable parser functions. Each function or tightly
coupled function cluster becomes an area.

## Tool bindings

Use `decompile_function`, `disassemble_function`, `get_xrefs_to`, and
`get_xrefs_from` for static analysis. Dynamic execution or fuzzing needs
separate scope and explicit human confirmation; do not add it here.

## Finding schema extensions

Record function name/address, binary build/version, static versus dynamic
confirmation, and store any crash input under `findings/evidence/<slug>/`.

## Recommended external skills

Consult these registry identifiers only when they match the selected
cell; they are on-demand references, not installed CLI skills:

- `tob-c-review`
- `tob-rust-review`
- `tob-constant-time-analysis`
- `tob-zeroize-audit`
- `tob-dwarf-expert`
