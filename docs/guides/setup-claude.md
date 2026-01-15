# Setting up FlowCheck with "Claude Code" (CLI)

[Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview) is an agentic coding tool that lives in your terminal. It is the primary way to use Claude for direct codebase manipulation.

## 1. Installation

Ensure you have Claude Code installed:

```bash
npm install -g @anthropic-ai/claude-code
```

## 2. Configure flowcheck as a Tool

Claude Code currently detects MCP servers through project-level or user-level configuration.

### Option A: Project Config (`.claude/config.json`)

If you want FlowCheck enabled for a specific project:

1. Create/edit `.claude.json` in your project root.
2. Add the `mcpServers` configuration:

```json
{
  "mcpServers": {
    "flowcheck": {
      "command": "/ABSOLUTE/PATH/TO/flowcheck/.venv/bin/python",
      "args": ["-m", "flowcheck.server"],
      "env": {
        "PYTHONPATH": "/ABSOLUTE/PATH/TO/flowcheck/src"
      }
    }
  }
}
```

### Option B: Global Config

(Note: Check Claude Code documentation for the latest global config path, typically `~/.claude/config.json` on macOS).

## 3. Usage

Start Claude Code in your terminal:

```bash
claude
```

Then simply ask it to perform FlowCheck tasks:

> "Run get_flow_state to check my repo health."

or

> "Verify if my changes match ticket #123."

Claude Code will execute the tools autonomously as part of its agentic loop.

---

# Setting up FlowCheck with Claude Desktop App

If you prefer using the desktop GUI application:

1. Edit `~/Library/Application Support/Claude/claude_desktop_config.json`.
2. Add the same `mcpServers` configuration block as above.
3. Restart the Claude Desktop app.
