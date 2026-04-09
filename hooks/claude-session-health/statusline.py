#!/usr/bin/env python3
"""
Claude Code statusLine script.
Reads session JSON from stdin, outputs a one-line status bar.

Context color thresholds:
  green  < 60%
  yellow 60-79%
  red    80%+  (with HIGH label)
"""
import sys
import json
import subprocess

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RED    = "\033[31m"
YELLOW = "\033[33m"
GREEN  = "\033[32m"

# ── Context window ─────────────────────────────────────────────
ctx = data.get("context_window", {})
pct = int(ctx.get("used_percentage") or 0)

BAR_WIDTH = 15
filled = int(pct * BAR_WIDTH / 100)
bar = "#" * filled + "-" * (BAR_WIDTH - filled)

if pct >= 80:
    ctx_color = BOLD + RED
    label = f"  {BOLD}{RED}COMPACT NOW{RESET}"
elif pct >= 60:
    ctx_color = YELLOW
    label = ""
else:
    ctx_color = GREEN
    label = ""

ctx_part = f"{ctx_color}ctx [{bar}] {pct}%{RESET}{label}"

# ── Model ───────────────────────────────────────────────────────
model = data.get("model", {}).get("display_name", "")

# ── Git branch ──────────────────────────────────────────────────
try:
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"],
        stderr=subprocess.DEVNULL, text=True, timeout=1
    ).stdout.strip()
except Exception:
    branch = ""

# ── Cost ────────────────────────────────────────────────────────
cost_usd = (data.get("cost") or {}).get("total_cost_usd") or 0
cost_part = f"${cost_usd:.3f}" if cost_usd >= 0.005 else ""

# ── Assemble ────────────────────────────────────────────────────
parts = [ctx_part]
if model:
    parts.append(f"{DIM}{model}{RESET}")
if branch:
    parts.append(branch)
if cost_part:
    parts.append(cost_part)

print(" | ".join(parts))
