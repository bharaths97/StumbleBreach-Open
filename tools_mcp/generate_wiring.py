"""Print the Claude Code (.mcp.json) and Codex (.codex/config.toml) wiring
for a stdio tool-server registry.

Do not hand-write MCP server `command`/`args`/`env` — this computes them via
`unified_agent.tools.build_tool_server_spec`, which works out the correct
`PYTHONPATH` and passes an explicit `env` to both backends (Codex does not
inherit the parent process's environment for MCP servers; Claude Code does,
but the same explicit env is used for both so behavior matches). See
the MCP wiring design notes on generating the wiring rather than
hand-writing it.

Usage:
    tools-env/.venv/bin/python -m tools_mcp.generate_wiring <server> <spec>

Example:
    tools-env/.venv/bin/python -m tools_mcp.generate_wiring recon \\
        tools_mcp.recon.registry:REGISTRY

Prints both a `.mcp.json` fragment and a `.codex/config.toml` fragment to
transcribe by hand into the real files (re-run whenever the venv path or
registry module layout changes, so the two configs don't drift from what
this actually produces).
"""

from __future__ import annotations

import json
import os
import sys

from unified_agent.tools import build_tool_server_spec


def render(server_name: str, registry_spec: str) -> None:
    for actor in ("claude", "codex"):
        spec = build_tool_server_spec(
            registry_spec,
            extra_env={"MCP_ACTOR": actor, "MCP_ROLE": "worker", "PATH": os.environ["PATH"]},
        )
        print(f"# --- {actor} ---")
        if actor == "claude":
            fragment = {
                "command": spec.command[0],
                "args": spec.command[1:],
                "env": spec.env,
            }
            print(json.dumps({server_name: fragment}, indent=2))
        else:
            print(f"[mcp_servers.{server_name}]")
            print(f'command = "{spec.command[0]}"')
            args_toml = ", ".join(f'"{a}"' for a in spec.command[1:])
            print(f"args = [{args_toml}]")
            env_toml = ", ".join(f'{k} = "{v}"' for k, v in spec.env.items())
            print(f"env = {{ {env_toml} }}")
        print()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(
            "usage: python -m tools_mcp.generate_wiring <server_name> <pkg.mod:REGISTRY>",
            file=sys.stderr,
        )
        raise SystemExit(2)
    render(sys.argv[1], sys.argv[2])
