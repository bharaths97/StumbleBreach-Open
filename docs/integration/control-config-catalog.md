# Control catalog

`dashboard/control_config.py` is the read-only inventory of operational knobs
that a future execution UI may expose. It is intentionally separate from
`config/target.env`: the dashboard never writes that file.

Each knob is classified as:

- `display-only`: show the authoritative value or gate result;
- `prepare-only`: select a known scope, queue row, role, or UI preference for a
  handoff preview;
- `confirm-required`: a bounded execution setting that needs an explicit
  operator confirmation before use;
- `forbidden`: no dashboard control exists for it.

Snapshots omit target, endpoint, and secret contents. A missing config is
reported as `missing`; a config with only the older `IN_SCOPE_TARGETS` shape is
reported as `legacy`. Neither condition is silently upgraded. An agent or
operator can review legacy records and record provenance during a backpatch.

The current wrappers provide fixed timeout caps, a 4,000-character inline
output ceiling, always-on receipt redaction, registered recon/webapp/blockchain
adapters, and known evidence paths. Cross-process concurrency and mutable
adapter enablement do not currently have authoritative controls, so snapshots
mark those as unavailable rather than inventing a setting.

The forbidden list is part of the contract: arbitrary commands or targets,
secrets, remote binding, redaction disablement, and autonomous agent dispatch
must remain absent from any future execution UI.
