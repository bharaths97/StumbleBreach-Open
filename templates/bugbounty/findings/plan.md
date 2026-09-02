# Test Plan

Maintained by the overseer role. Update status as work progresses.

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | <first test item> | not started | |

## Pre-reboot / pre-service-restart checklist

Before rebooting the target or restarting any agent/service:

1. Copy any DLL/binary you plan to analyze to a safe location outside the
   agent's protected tree (filter drivers may re-arm on reboot)
2. Copy scan-policy XMLs, config files, log snapshots
3. Note any filter drivers (`fltmc` on Windows) that may re-arm
4. Commit evidence captured so far

## POC output validation

After running each POC script:

1. Check the output file line count — is it complete?
2. If sparse or empty, re-run with verbose/debug flags
3. Compare output sections against the expected sections listed in the
   script's header comment
