# Pavilion local-service contract

StumbleBreach owns its dashboard data and remains useful when Pavilion is
stopped. Pavilion owns service discovery, health display, navigation, proxying,
and explicit local-service start/stop requests. It does not receive a copy of
the dashboard read model.

## Service identity

The checked-in business card is [`dashboard/pavilion_manifest.json`](../../dashboard/pavilion_manifest.json).
Its local registry entry is machine-specific and remains ignored. The registry
resolves the manifest path on the operator's machine; no absolute checkout
path, credential, or engagement data belongs in this contract.

```json
{
  "schema_version": 1,
  "name": "StumbleBreach Dashboard",
  "port": 4400,
  "health_check": { "method": "GET", "path": "/api/health", "expect_status": 200 },
  "controllable": true,
  "start_command": "python3 lifecycle.py start",
  "stop_command": "python3 lifecycle.py stop"
}
```

The relative commands call the service-owned `dashboard/lifecycle.py` wrapper.
The dashboard API remains GET-only; only Pavilion's explicit local-service
controls can invoke lifecycle commands.

## Health and lifecycle

Pavilion checks `GET http://127.0.0.1:4400/api/health`. The dashboard remains
independently usable when Pavilion is unavailable. Health state means:

| Observation | Pavilion state | Meaning |
| --- | --- | --- |
| Expected HTTP response | `up` | Dashboard answered health route. |
| Connection refusal/timeout | `down` | Dashboard is not reachable. |
| Missing or malformed health configuration | `unknown` | Availability cannot be established. |

Health never authorizes testing, tool calls, queue changes, submissions, or
lifecycle actions. Start/stop is a separate explicit operator action in
Pavilion. The wrapper uses a private PID file, binds the dashboard to loopback,
and does not supervise, restart, or expose a remote control API.

## Proxy

Pavilion registers the service under one lowercase path segment and strips that
prefix before forwarding to loopback:

| Pavilion request | Dashboard request |
| --- | --- |
| `/stumblebreach/` | `/` |
| `/stumblebreach/api/health` | `/api/health` |
| `/stumblebreach/api/<route>` | `/api/<route>` |

The proxy preserves method and query string, returns a clear `502` when the
backend cannot be reached, and never proxies Pavilion's own `/api/services`
control routes into the dashboard. Dashboard page assets and API URLs remain
relative so standalone and mounted operation both work.

## Acceptance checks

From the StumbleBreach root:

```sh
python3 -m unittest tests/test_pavilion_contract.py tests/test_dashboard_lifecycle.py
```

This verifies the business card, loopback-only health behavior, unavailable
backend mapping, prefix mapping, relative lifecycle commands, and actual
start/stop behavior. Pavilion's own `npm test` is the downstream proxy and
control-panel gate.

## Portable shared-shell backpatch

`dashboard/public/sidebar-drawer.js` is a StumbleBreach copy of the Pavilion
drawer helper. Its initial render applies saved/default state synchronously
and keeps desktop workspace shifting separate from the mobile-only backdrop.
When another consumer shows the same first-paint or overlay symptom, backpatch
the shared helper behavior rather than adding per-repository geometry overrides.
