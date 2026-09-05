# Recon and evidence guidance

The recon manifest is optional context. It can explain why an in-scope asset
deserves review, but it never authorizes testing or selects queue work.
`scope.md`, `coverage.json`, `queue.md`, finding readiness, and Karma remain
the authorities.

## Manifest hygiene

- Record ownership confidence and an explicit anchor for every trusted asset.
- Keep keyword, breach-dataset, repository, mobile-store, and cloud results
  untrusted until an ownership anchor is recorded.
- Quarantine unowned assets and junk paths. A 200 or 403 response does not
  defeat soft-404 or ownership checks.
- Store only secret references and a redaction reference; never store cookies,
  tokens, passwords, authorization headers, API keys, or raw secret values.
- Do not add queue rows or automatic selection fields to a manifest. A human
  must select a queue row and the selected work must map to an owning coverage
  cell.
- Keep CTF artifact and flag tracking in the CTF workflow, not this manifest.

## Evidence hygiene

Redact cookies, tokens, authorization headers, credentials, and unrelated
user PII before preserving evidence. Sanitize HAR files and terminal output;
capture screenshots after the reproducible request and retain only the useful
viewport. Evidence filenames should identify the finding, step, and provenance
without embedding secrets. Record test-account identity and relevant group
membership. Preserve the exact reproducible command and the smallest output
slice that demonstrates the claim.

## Finding lifecycle

Use one lead per finding, not one finding per sweep campaign:

`lead -> reproduced -> drafted -> adversarially reviewed -> ready -> submitted/closed`

Every state transition records four things: a reason, evidence references, an
owner, and the next decision. “Reproduced” is not “ready”; readiness still
requires the existing finding gate, coverage linkage, queue authority, and
Karma review.
