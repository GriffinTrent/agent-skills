# Claude Session Health Hooks

Two Claude Code hooks that give you live visibility into context window usage and prevent silent context loss before auto-compaction.

## What's included

### `statusline.py` — Live context bar
Displays a persistent status bar at the bottom of your terminal showing:
- Context window usage with a color-coded progress bar
- Current model name
- Git branch
- Session cost

**Color thresholds:**
- Green — under 60% used
- Yellow — 60–79% (start thinking about `/compact`)
- Bold red + "COMPACT NOW" — 80%+ (act before auto-compact fires)

### `precompact.py` — Auto-compact blocker
Fires before any auto-compaction event. If no session snapshot exists in `CLAUDE.md`, it blocks compaction and prints a template for you to fill in. Once `CLAUDE.md` has the snapshot, manual `/compact` proceeds immediately.

**Behavior:**
- Auto-compact → blocked until snapshot written to `CLAUDE.md`
- Manual `/compact` → always passes through
- Snapshot already present → allows auto-compact

## Setup

1. Copy both scripts to `~/.claude/hooks/`:
   ```bash
   mkdir -p ~/.claude/hooks
   cp precompact.py statusline.py ~/.claude/hooks/
   chmod +x ~/.claude/hooks/statusline.py
   ```

2. Add to `~/.claude/settings.json`:
   ```json
   {
     "statusLine": {
       "type": "command",
       "command": "python3 ~/.claude/hooks/statusline.py",
       "padding": 1
     },
     "hooks": {
       "PreCompact": [
         {
           "matcher": "",
           "hooks": [
             {
               "type": "command",
               "command": "python3 ~/.claude/hooks/precompact.py"
             }
           ]
         }
       ]
     }
   }
   ```

3. Restart Claude Code. The status bar appears immediately; the PreCompact hook fires the next time auto-compact would trigger.

## Workflow

Watch the status bar. When it turns **yellow** (~60%), run:
```
/compact focus on [what you're working on]
```

If you miss it and hit 80%, the bar turns red. If auto-compact tries to fire before you've captured context, the PreCompact hook blocks it and tells you exactly what to write to `CLAUDE.md`.

## Requirements

- Python 3.8+
- Claude Code with hooks support (`~/.claude/settings.json`)
