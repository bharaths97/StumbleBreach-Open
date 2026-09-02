# Tooling and MCP source

`tools_mcp/` contains reusable MCP registry source for reconnaissance, web
application, and blockchain work. Each registry uses the shared scope guard:
the tool checks the private engagement configuration before it starts a
subprocess and records the result in that engagement's local evidence flow.

The repository intentionally does not bundle third-party binaries, wordlists,
virtual environments, GUI applications, credentials, or target configuration.
Those are local operator dependencies.

## First use

1. Create a local environment at `tools-env/.venv`.
2. Install the MCP runtime and compatible `unified_agent` package used by your
   agent integration.
3. Install only the command-line tools approved for the engagement.
4. Optionally place SecLists in `tools-env/seclists/`.
5. Run the doctor:

   ```sh
   tools-env/.venv/bin/python tools_mcp/doctor.py
   ```

The doctor reports what is missing and checks the MCP registries without
requiring a real target. `tools_mcp/generate_wiring.py` prints Claude Code and
Codex configuration fragments for a chosen registry; review the generated
configuration before adding it to local agent settings.

Tool source is not authorization. Configure a private engagement scope before
invoking a tool against any system.
