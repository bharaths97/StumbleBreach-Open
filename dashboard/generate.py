#!/usr/bin/env python3
"""Regenerate the local engagement dashboard from live git state.

Reads every engagement branch via
`git show`/`git ls-tree` only -- never `git checkout` -- so this can be
run from wherever you happen to be checked out (main, an engagement
branch, doesn't matter) without switching you off your current branch.
Same property `/pentest-planner` and `/tools-curator` already rely on.

Manual regeneration only, no watch/daemon mode:

    python dashboard/generate.py > dashboard/index.html

Optional tooling-health panel (skipped if the file doesn't exist):

    tools-env/.venv/bin/python tools_mcp/doctor.py --json > tools_mcp/doctor-report.json
    python dashboard/generate.py > dashboard/index.html
"""

from __future__ import annotations

import html
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCTOR_REPORT_PATH = REPO_ROOT / "tools_mcp" / "doctor-report.json"

_NON_FINDING_FILES = {"TEMPLATE-finding.md", "plan.md"}
_NON_CHALLENGE_DIRS = {"TEMPLATE", "intake"}


def _git(*args: str) -> str | None:
    """Run a git command, returning stdout, or None if it fails (e.g. path doesn't exist on that ref)."""
    result = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else None


def git_show(ref: str, path: str) -> str | None:
    return _git("show", f"{ref}:{path}")


def git_ls_tree(ref: str, path: str) -> list[tuple[str, str]]:
    """(kind, name) pairs for entries directly under `path` on `ref`. Empty list if the path doesn't exist."""
    out = _git("ls-tree", ref, path)
    if not out:
        return []
    entries = []
    for line in out.splitlines():
        meta, name = line.split("\t", 1)
        _mode, kind, _sha = meta.split()
        entries.append((kind, name))
    return entries


def parse_md_table(text: str) -> list[dict[str, str]]:
    """Generic markdown-table parser: header row + separator + data rows, matched by column name."""
    lines = [line for line in text.splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        return []
    header = [c.strip() for c in lines[0].strip("|").split("|")]
    rows = []
    for line in lines[2:]:  # skip header + `---` separator
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != len(header):
            continue
        rows.append(dict(zip(header, cells)))
    return rows


def _extract_product_line(scope_text: str) -> str | None:
    """Pull scope.md's '- Product: ...' line, merging soft-wrapped continuation lines."""
    lines = scope_text.splitlines()
    for i, line in enumerate(lines):
        match = re.match(r"^-\s*Product:\s*(.+)$", line.strip())
        if not match:
            continue
        parts = [match.group(1).strip()]
        for cont in lines[i + 1 :]:
            stripped = cont.strip()
            if not stripped or stripped.startswith(("-", "#")):
                break
            parts.append(stripped)
        return " ".join(parts)
    return None


def last_activity_timestamp(log_text: str) -> str | None:
    """Timestamp of the last non-comment line in an activity.log (ISO8601 sorts correctly as a string)."""
    lines = [line.strip() for line in log_text.splitlines() if line.strip() and not line.strip().startswith("#")]
    if not lines:
        return None
    match = re.match(r"^(\S+)", lines[-1])
    return match.group(1) if match else lines[-1]


def parse_engagements() -> list[dict[str, str]]:
    """ENGAGEMENTS.md is read from `main` specifically, regardless of the current checkout (per the plan)."""
    text = git_show("main", "ENGAGEMENTS.md")
    if not text:
        return []
    rows = parse_md_table(text)
    return [
        {
            "name": row.get("Name", "").strip("` "),
            "type": row.get("Type", "").strip(),
            "branch": row.get("Branch", "").strip("` "),
            "status": row.get("Status", "").strip(),
            "created": row.get("Created", "").strip(),
            "description": row.get("Description", "").strip(),
        }
        for row in rows
        if row.get("Name")
    ]


def analyze_bugbounty(branch: str) -> dict:
    plan_text = git_show(branch, "findings/plan.md")
    plan_rows = parse_md_table(plan_text) if plan_text else []
    status_counts: dict[str, int] = {}
    for row in plan_rows:
        status = row.get("Status", "").strip().lower() or "unknown"
        status_counts[status] = status_counts.get(status, 0) + 1
    total_items = len(plan_rows)
    done = status_counts.get("done", 0)

    scope_summary = _extract_product_line(git_show(branch, "scope.md") or "")

    activity_text = git_show(branch, "logs/activity.log")
    last_activity = last_activity_timestamp(activity_text) if activity_text else None

    findings_count = sum(
        1
        for kind, name in git_ls_tree(branch, "findings/")
        if kind == "blob" and name.rsplit("/", 1)[-1].endswith(".md") and name.rsplit("/", 1)[-1] not in _NON_FINDING_FILES
    )

    return {
        "scope_summary": scope_summary,
        "plan_total": total_items,
        "plan_done": done,
        "plan_status_counts": status_counts,
        "findings_count": findings_count,
        "last_activity": last_activity,
    }


_CHALLENGE_LINE_RE = re.compile(
    r"^[-*]?\s*([\w.\-]+):\s*(.+?)\s*\((\d+|\?)\s*/\s*(\d+|\?)\)\s*$"
)


def analyze_ctf(branch: str) -> dict:
    status_text = git_show(branch, "STATUS.md") or ""
    challenges = []
    in_section = False
    for line in status_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Challenges"):
            in_section = True
            continue
        if in_section and stripped.startswith("##"):
            break
        if in_section:
            match = _CHALLENGE_LINE_RE.match(stripped)
            if match:
                name, state, captured, total = match.groups()
                challenges.append({"name": name, "state": state, "captured": captured, "total": total})

    captured_total = sum(int(c["captured"]) for c in challenges if c["captured"] != "?")
    flags_total = sum(int(c["total"]) for c in challenges if c["total"] != "?")
    unknown_totals = any(c["total"] == "?" for c in challenges)

    last_activity = None
    for kind, name in git_ls_tree(branch, "challenges/"):
        challenge_name = name.rsplit("/", 1)[-1]
        if kind != "tree" or challenge_name in _NON_CHALLENGE_DIRS:
            continue
        log_text = git_show(branch, f"{name}/activity.log")
        if log_text:
            ts = last_activity_timestamp(log_text)
            if ts and (last_activity is None or ts > last_activity):
                last_activity = ts

    return {
        "challenges": challenges,
        "flags_captured": captured_total,
        "flags_total": flags_total,
        "flags_total_unknown": unknown_totals,
        "last_activity": last_activity,
    }


def load_doctor_report() -> dict | None:
    if not DOCTOR_REPORT_PATH.exists():
        return None
    try:
        return json.loads(DOCTOR_REPORT_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def build_data() -> dict:
    engagements = []
    for eng in parse_engagements():
        analysis = analyze_bugbounty(eng["branch"]) if eng["type"] == "bugbounty" else analyze_ctf(eng["branch"])
        engagements.append({**eng, "analysis": analysis})
    return {"engagements": engagements, "doctor_report": load_doctor_report()}


def _esc(value) -> str:
    return html.escape(str(value)) if value is not None else ""


def render_bugbounty_card(eng: dict) -> str:
    a = eng["analysis"]
    fraction = f"{a['plan_done']}/{a['plan_total']}" if a["plan_total"] else "no plan items"
    scope = a["scope_summary"] or "(scope not filled in yet)"
    last_activity = a["last_activity"] or "(no activity logged yet)"
    return f"""
    <div class="card">
      <div class="card-header">
        <span class="badge badge-bb">bug-bounty</span>
        <h2>{_esc(eng['name'])}</h2>
        <span class="status status-{_esc(eng['status'])}">{_esc(eng['status'])}</span>
      </div>
      <p class="branch">branch: <code>{_esc(eng['branch'])}</code> &middot; created {_esc(eng['created'])}</p>
      <p class="desc">{_esc(eng['description'])}</p>
      <dl>
        <dt>Scope</dt><dd>{_esc(scope)}</dd>
        <dt>Plan progress</dt><dd>{_esc(fraction)} done</dd>
        <dt>Findings</dt><dd>{_esc(a['findings_count'])}</dd>
        <dt>Last activity</dt><dd>{_esc(last_activity)}</dd>
      </dl>
    </div>"""


def render_ctf_card(eng: dict) -> str:
    a = eng["analysis"]
    total_display = f"{a['flags_total']}{'+' if a['flags_total_unknown'] else ''}"
    flags = f"{a['flags_captured']}/{total_display}"
    last_activity = a["last_activity"] or "(no activity logged yet)"
    challenge_rows = "".join(
        f"<li>{_esc(c['name'])}: {_esc(c['state'])} ({_esc(c['captured'])}/{_esc(c['total'])})</li>"
        for c in a["challenges"]
    ) or "<li>(no challenges tracked yet)</li>"
    return f"""
    <div class="card">
      <div class="card-header">
        <span class="badge badge-ctf">CTF</span>
        <h2>{_esc(eng['name'])}</h2>
        <span class="status status-{_esc(eng['status'])}">{_esc(eng['status'])}</span>
      </div>
      <p class="branch">branch: <code>{_esc(eng['branch'])}</code> &middot; created {_esc(eng['created'])}</p>
      <p class="desc">{_esc(eng['description'])}</p>
      <dl>
        <dt>Flags</dt><dd>{_esc(flags)} captured</dd>
        <dt>Last activity</dt><dd>{_esc(last_activity)}</dd>
      </dl>
      <ul class="challenges">{challenge_rows}</ul>
    </div>"""


def render_tooling_panel(report: dict | None) -> str:
    if report is None:
        return ""

    def row(ok: bool, label: str, detail: str) -> str:
        cls = "ok" if ok else "miss"
        return f'<tr class="{cls}"><td>{_esc(label)}</td><td>{"OK" if ok else "MISSING"}</td><td>{_esc(detail)}</td></tr>'

    rows = []
    for name, r in report.get("stdio_servers", {}).items():
        detail = f"{r.get('tool_count', '?')} tools" if r["ok"] else r["detail"]
        rows.append(row(r["ok"], name, detail))
    if "metasploit" in report:
        m = report["metasploit"]
        rows.append(row(m["ok"], "metasploit", f"{m.get('tool_count', '?')} tools" if m["ok"] else m["detail"]))
    for name, r in report.get("external_servers", {}).items():
        rows.append(row(r["ok"], name, r["detail"]))
    for binary, r in report.get("binaries", {}).items():
        # Install commands rendered as plain copyable text ONLY -- never a
        # button that executes anything: a non-negotiable security decision so
        # the dashboard can never be coerced into running an install command.
        detail = r["path"] if r["installed"] else f"install: {r['install_command']}"
        rows.append(row(r["installed"], binary, detail))

    return f"""
    <section class="tooling">
      <h2>Tooling health</h2>
      <table>
        <thead><tr><th>Server/binary</th><th>Status</th><th>Detail</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </section>"""


PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>StumbleBreach engagement dashboard</title>
<style>
  body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem;
         background: #0f1115; color: #e6e6e6; }}
  h1 {{ font-size: 1.4rem; }}
  h2 {{ font-size: 1.1rem; margin: 0; }}
  .generated-at {{ color: #888; font-size: 0.85rem; margin-bottom: 1.5rem; }}
  .card {{ background: #1b1e26; border: 1px solid #2a2e38; border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 1rem; }}
  .card-header {{ display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.3rem; }}
  .badge {{ font-size: 0.7rem; padding: 0.15rem 0.5rem; border-radius: 4px; text-transform: uppercase; }}
  .badge-bb {{ background: #2d4a6b; }}
  .badge-ctf {{ background: #5a3a6b; }}
  .status {{ margin-left: auto; font-size: 0.75rem; padding: 0.1rem 0.5rem; border-radius: 4px; background: #333; }}
  .status-active {{ background: #2d6b3a; }}
  .status-paused {{ background: #6b5a2d; }}
  .status-done {{ background: #444; }}
  .branch code {{ background: #262a33; padding: 0.1rem 0.4rem; border-radius: 4px; }}
  .branch, .desc {{ color: #b8b8b8; font-size: 0.9rem; }}
  dl {{ display: grid; grid-template-columns: max-content 1fr; gap: 0.2rem 1rem; margin: 0.75rem 0 0; }}
  dt {{ color: #999; font-size: 0.85rem; }}
  dd {{ margin: 0; font-size: 0.9rem; }}
  ul.challenges {{ margin: 0.5rem 0 0; padding-left: 1.2rem; font-size: 0.85rem; color: #ccc; }}
  section.tooling table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
  section.tooling th, section.tooling td {{ text-align: left; padding: 0.3rem 0.6rem; border-bottom: 1px solid #2a2e38; }}
  tr.ok td:nth-child(2) {{ color: #5fbf6f; }}
  tr.miss td:nth-child(2) {{ color: #d9776b; }}
  .empty {{ color: #888; font-style: italic; }}
</style>
</head>
<body>
<h1>StumbleBreach engagement dashboard</h1>
<p class="generated-at">Regenerated on demand from live git state (no branch checkout involved) -- run
  <code>python dashboard/generate.py &gt; dashboard/index.html</code> to refresh. Not a live-updating page.</p>
{cards}
{tooling}
</body>
</html>
"""


def render(data: dict) -> str:
    if not data["engagements"]:
        cards = '<p class="empty">No engagements in ENGAGEMENTS.md.</p>'
    else:
        cards = "".join(
            render_ctf_card(eng) if eng["type"] == "ctf" else render_bugbounty_card(eng)
            for eng in data["engagements"]
        )
    tooling = render_tooling_panel(data["doctor_report"])
    return PAGE_TEMPLATE.format(cards=cards, tooling=tooling)


def main() -> None:
    sys.stdout.write(render(build_data()))


if __name__ == "__main__":
    main()
