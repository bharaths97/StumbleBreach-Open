"""Record that a tool's update command was just run.

See the MCP wiring design notes. This does not run the
update itself -- run the real command from `UPDATE_COMMANDS`
(`tools_mcp/hub_guard/enforce.py`) yourself, then call this to record
"now" in `tools_mcp/.update-timestamps.json` (untracked, same tier as
everything else here). No parsing of the tool's own output; this is
just you telling the system "I did this," for `tools_mcp/doctor.py`'s
staleness check to read back later.

Usage:
    tools-env/.venv/bin/python tools_mcp/mark_updated.py <tool>
"""

from __future__ import annotations

import datetime
import json
import sys

from tools_mcp.hub_guard.enforce import UPDATE_COMMANDS, _TIMESTAMPS_PATH


def mark_updated(tool: str) -> str:
    if tool not in UPDATE_COMMANDS:
        raise SystemExit(
            f"{tool!r} has no entry in UPDATE_COMMANDS -- known tools: {sorted(UPDATE_COMMANDS)}"
        )
    timestamps = json.loads(_TIMESTAMPS_PATH.read_text()) if _TIMESTAMPS_PATH.exists() else {}
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    timestamps[tool] = now
    _TIMESTAMPS_PATH.write_text(json.dumps(timestamps, indent=2))
    return now


def main() -> None:
    if len(sys.argv) != 2:
        print(
            f"usage: python tools_mcp/mark_updated.py <tool>\nknown tools: {sorted(UPDATE_COMMANDS)}",
            file=sys.stderr,
        )
        raise SystemExit(2)
    tool = sys.argv[1]
    now = mark_updated(tool)
    print(f"recorded {tool!r} as updated at {now}")


if __name__ == "__main__":
    main()
