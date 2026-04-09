#!/usr/bin/env python3
"""
PreCompact hook — auto-blocks context compaction until a session snapshot
is written to CLAUDE.md. Manual /compact always passes through.
"""
import sys
import json
import os
import subprocess
import datetime

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

trigger = data.get("trigger", "unknown")
cwd = os.getcwd()
claude_md_path = os.path.join(cwd, "CLAUDE.md")

# Manual /compact always passes through — user made a deliberate choice
if trigger == "manual":
    sys.exit(0)

# Auto-compact: check if a snapshot was already written this session
MARKER = "PRECOMPACT_SNAPSHOT"
if os.path.exists(claude_md_path):
    with open(claude_md_path) as f:
        if MARKER in f.read():
            print("Pre-compact snapshot already in CLAUDE.md — allowing compaction.")
            sys.exit(0)

# Gather context we can access from the shell
try:
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"],
        stderr=subprocess.DEVNULL, text=True, cwd=cwd
    ).stdout.strip() or "n/a"
except Exception:
    branch = "n/a"

ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
has_claude_md = os.path.exists(claude_md_path)
action = "Append this section to" if has_claude_md else "Create CLAUDE.md with"

print()
print("=" * 62)
print("AUTO-COMPACT BLOCKED — session snapshot required first")
print("=" * 62)
print(f"  Branch : {branch}")
print(f"  Time   : {ts}")
print(f"  File   : {claude_md_path}")
print()
print(f"{action} {claude_md_path}.")
print("Fill in the brackets with actual session content, then run /compact.")
print()
print(f"<!-- {MARKER} {ts} -->")
print(f"## Pre-Compact Context — {ts}")
print()
print("**Goal:** [one sentence — what are we building or fixing this session]")
print()
print("**Key decisions:**")
print("- [decision + rationale]")
print()
print("**Open tasks:**")
print("- [ ] [next step to pick up after resuming]")
print()
print("**Do NOT:** [constraint, anti-goal, or approach to avoid]")
print()
print(f"<!-- END_{MARKER} -->")
print()
print("After writing: run /compact (manual compact is always allowed through).")
print("=" * 62)

sys.exit(2)  # Block auto-compaction
