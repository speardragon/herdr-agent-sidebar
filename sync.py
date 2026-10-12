#!/usr/bin/env python3
"""Keep tab IDs and compact, project-grouped Agent sidebar metadata in sync."""
from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys

from animations import STATE, ensure_started, glyph_for, tab_tokens


herdr = os.environ.get("HERDR_BIN_PATH", "herdr")
source = "speardragon.agent-sidebar"
rule = "────────────────────────────"
logos = {"claude": "\ue1a0", "codex": "\ue1a1", "opencode": "\ue1a2", "pi": "\ue1a9", "grok": "\ue1b1", "agy": "\ue1b2"}
marks = {"working": "●", "done": "✓", "blocked": "?", "idle": "○", "unknown": "◌"}


def run(args: list[str], expect_json: bool = True):
    result = subprocess.run([herdr, *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"herdr exited {result.returncode}")
    return json.loads(result.stdout) if expect_json else None


def sidebar_tokens(workspaces: list[dict], agents: list[dict]) -> dict[str, dict[str, str]]:
    """Place a header on the first visible agent of each contiguous workspace."""
    labels = {w["workspace_id"]: w.get("label") or w["workspace_id"] for w in workspaces}
    result = {}
    previous = None
    for index, agent in enumerate(agents):
        workspace_id = agent.get("workspace_id")
        first = workspace_id != previous
        last = index + 1 == len(agents) or agents[index + 1].get("workspace_id") != workspace_id
        result[agent["pane_id"]] = {
            "agents_group": labels.get(workspace_id, workspace_id or "") if first else "",
            "agents_group_end": rule[:22] if last else "",
            # Metadata strips leading whitespace. A zero-width space anchors the
            # padding; Herdr then draws every logo at the same column (3 cells).
            "agents_logo": ("" if first else "\u200b  ") + logos.get(agent.get("agent"), "◇"),
            "agents_mark": glyph_for(agent.get("agent_status")),
        }
        previous = workspace_id
    return result


def main() -> None:
    ensure_started()
    workspaces = run(["workspace", "list"])["result"]["workspaces"]
    agents = run(["agent", "list"])["result"]["agents"]
    tabs = {t["tab_id"]: t["label"] for t in run(["tab", "list"])["result"]["tabs"]}
    agent_tabs = {a["pane_id"]: tab_tokens(a, tabs) for a in agents}
    grouped = sidebar_tokens(workspaces, agents)
    labels = {w["workspace_id"]: w.get("label") or w["workspace_id"] for w in workspaces}
    panes = run(["pane", "list"])["result"]["panes"]
    for pane in panes:
        pane_id, tab_id = pane.get("pane_id"), pane.get("tab_id")
        if not pane_id or not tab_id:
            continue
        agent, workspace = pane.get("agent") or "", labels.get(pane.get("workspace_id"), "")
        desired = {
            "tab_id": tab_id,
            "rule": rule,
            "headline": f"{agent} | {workspace}" if agent and workspace else agent or workspace,
            **agent_tabs.get(pane_id, {"agents_tab_" + status: "" for status in ("working", "done", "blocked", "idle", "unknown")}),
            **grouped.get(pane_id, {"agents_group": "", "agents_group_end": "", "agents_logo": "", "agents_mark": ""}),
        }
        current = pane.get("tokens", {})
        changed = {key: value for key, value in desired.items() if current.get(key, "") != value}
        if not changed:
            continue
        args = ["pane", "report-metadata", pane_id, "--source", source]
        for key, value in changed.items():
            args.extend(["--token", f"{key}={value}"] if value else ["--clear-token", key])
        try:
            run(args, expect_json=False)
        except RuntimeError as error:
            print(f"{pane_id}: {error}", file=sys.stderr)


if __name__ == "__main__":
    try:
        # Serialize event hooks so an older snapshot cannot overwrite a newer one.
        with (STATE / "sync.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            main()
    except Exception as error:
        print(error, file=sys.stderr)
        sys.exit(1)
