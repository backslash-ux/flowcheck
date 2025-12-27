# FlowCheck MCP Server

<div align="center">

**🛡️ A Git Hygiene Safety Layer for AI-First Development**

_Keep your AI coding assistants honest with automatic commit hygiene checks_

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

</div>

---

## Why FlowCheck?

AI coding assistants are incredibly productive—but they can also create **massive, hard-to-review changesets** in a single session. FlowCheck acts as a safety layer that:

- 🔍 **Monitors Git state** in real-time during AI-assisted coding
- ⚡ **Nudges agents** to make checkpoint commits before changes get too large
- 📊 **Tracks flow health** (time since commit, lines changed, files modified)
- 🤖 **Designed for AI agents** with enforceable rules and clear tool interfaces

> Think of FlowCheck as a "smart fitness watch" for your codebase—it doesn't block, it nudges.

## AI-First Design

FlowCheck is built specifically for the **agentic coding** workflow:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   AI Agent      │────▶│   FlowCheck     │────▶│   Git Repo      │
│  (Claude, etc)  │◀────│   MCP Server    │◀────│   (.git)        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │
        │   "status: warning"   │
        │   "500+ lines pending"│
        ▼                       │
   Agent pauses and             │
   suggests checkpoint ◀────────┘
```

### Agent Rules (Recommended)

Copy [`rules/flowcheck-rules.md`](rules/flowcheck-rules.md) to your AI tool's rules directory:

```bash
# For Cursor
cp rules/flowcheck-rules.md .cursor/rules/

# For Claude Projects
cp rules/flowcheck-rules.md .claude/rules/

# For other tools
cp rules/flowcheck-rules.md .agent/rules/
```

This instructs AI agents to **automatically check Git hygiene** before starting tasks and to pause when thresholds are exceeded.

## Quick Start

### Installation

```bash
git clone https://github.com/your-org/flowcheck.git
cd flowcheck

python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Claude Desktop Integration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "flowcheck": {
      "command": "/path/to/flowcheck/.venv/bin/python",
      "args": ["-m", "flowcheck.server"],
      "env": {
        "PYTHONPATH": "/path/to/flowcheck/src"
      }
    }
  }
}
```

## MCP Tools

| Tool                  | Purpose                                              |
| --------------------- | ---------------------------------------------------- |
| `get_flow_state`      | Returns current metrics (time, lines, files, status) |
| `get_recommendations` | Returns actionable nudges based on thresholds        |
| `set_rules`           | Dynamically adjust thresholds                        |

### Example: `get_flow_state`

```json
{
  "minutes_since_last_commit": 45,
  "uncommitted_lines": 520,
  "uncommitted_files": 8,
  "branch_name": "feature/api-refactor",
  "status": "warning"
}
```

### Example: `get_recommendations`

```json
{
  "recommendations": [
    "📊 You have 520 uncommitted lines. Consider splitting into focused commits.",
    "💡 Tip: Large changesets can be split by domain (backend vs frontend)."
  ],
  "status": "warning"
}
```

## Configuration

FlowCheck uses `~/.flowcheck/config.json`:

```json
{
  "max_minutes_without_commit": 60,
  "max_lines_uncommitted": 500
}
```

| Parameter                    | Default | Description                          |
| ---------------------------- | ------- | ------------------------------------ |
| `max_minutes_without_commit` | 60      | Minutes before suggesting checkpoint |
| `max_lines_uncommitted`      | 500     | Lines before suggesting split        |

## Status Levels

| Status    | Meaning                             |
| --------- | ----------------------------------- |
| `ok`      | All metrics within thresholds       |
| `warning` | One or more thresholds exceeded     |
| `danger`  | Thresholds exceeded by 1.5x or more |

## Development

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/flowcheck
```

## Philosophy

FlowCheck embodies the principle that **good Git hygiene enables good AI collaboration**:

1. **Smaller commits** are easier for humans to review and audit
2. **Frequent checkpoints** prevent losing work during long sessions
3. **Clean history** makes it easier to understand what the AI changed
4. **Non-blocking nudges** preserve developer autonomy

## License

MIT
