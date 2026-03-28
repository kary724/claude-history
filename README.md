# Claude History

A local web viewer for browsing, searching, and managing your Claude Code conversation history.

![screenshot](screenshot.png)

## Features

- 📋 Browse all past conversations, grouped by date
- 🔍 Real-time search across conversation content
- 🏷️ Auto-tagging by topic (IoT, Product Design, Coding, etc.)
- 🧠 AI-generated titles via Claude API (cached locally, no repeated calls)
- 📊 Token usage stats per session (input / cache / output)
- 🗑️ Move conversations to Trash with one click
- ▶️ Resume any conversation in terminal with `claude --resume`

## Requirements

- macOS
- Python 3.9+
- Claude Code installed (`~/.claude/` directory exists)

## Installation

```bash
git clone https://github.com/kary724/claude-history.git
cd claude-history
```

No dependencies required — uses Python standard library only.

## Usage

```bash
python3 server.py
```

Then open [http://localhost:8765](http://localhost:8765) in your browser.

### macOS Quick Launch (optional)

Create a file on your Desktop named `Claude History.command`:

```bash
#!/bin/zsh
lsof -ti:8765 | xargs kill -9 2>/dev/null
nohup python3 /path/to/claude-history/server.py > /tmp/claude-history.log 2>&1 &
sleep 1.5
open http://localhost:8765
exit
```

```bash
chmod +x ~/Desktop/Claude\ History.command
```

Double-click to launch.

## AI Title Generation (optional)

The tool automatically generates a short title for each conversation using the Claude API. Titles are cached in `titles.json` and never re-generated.

Requires an API key in `~/.claude/settings.json` (already configured if you use Claude Code):

```json
{
  "env": {
    "ANTHROPIC_API_KEY": "sk-...",
    "ANTHROPIC_BASE_URL": "https://api.anthropic.com"
  }
}
```

Without an API key, the tool still works — conversation titles fall back to the first message.

## Files

```
claude-history/
  server.py     # Python backend server
  index.html    # Frontend UI
  README.md     # This file
```

`titles.json` and `sessions_cache.json` are auto-generated on first run.

## Notes

- Deleted conversations are moved to the macOS Trash, not permanently deleted
- The server only listens on localhost — not exposed to the network
- All data stays local; only conversation summaries are sent to the Claude API for title generation
