# FlowCheck MCP Server

A local "safety layer" MCP server that provides non-blocking "flow health" nudges for developers. It monitors Git activity and provides recommendations for better commit hygiene without blocking developer momentum.

## Features

- **Non-blocking nudges**: Gentle suggestions, never prevents commits
- **Privacy-first**: All analysis stays on your machine
- **Configurable thresholds**: Customize to your workflow
- **MCP-compatible**: Works with Claude Desktop, VS Code, and other MCP clients

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/flowcheck.git
cd flowcheck

# Install with pip
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

### Running the Server

```bash
# Run with stdio transport (for MCP clients)
python -m flowcheck.server

# Run with HTTP transport (for testing)
fastmcp run src/flowcheck/server.py:mcp --transport http --port 8000
```

### Claude Desktop Integration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "flowcheck": {
      "command": "python",
      "args": ["-m", "flowcheck.server"]
    }
  }
}
```

## Configuration

FlowCheck uses a JSON config file at `~/.flowcheck/config.json`:

```json
{
  "max_minutes_without_commit": 60,
  "max_lines_uncommitted": 500
}
```

### Configuration Options

| Parameter                    | Default | Description                                      |
| ---------------------------- | ------- | ------------------------------------------------ |
| `max_minutes_without_commit` | 60      | Minutes before suggesting a checkpoint commit    |
| `max_lines_uncommitted`      | 500     | Lines changed before suggesting to split changes |

## MCP Tools

### `get_flow_state`

Returns current flow health metrics for a repository.

**Parameters:**

- `repo_path` (string): Path to the Git repository

**Returns:**

```json
{
  "minutes_since_last_commit": 45,
  "uncommitted_lines": 120,
  "uncommitted_files": 3,
  "branch_name": "feature/new-api",
  "status": "ok"
}
```

### `get_recommendations`

Returns actionable suggestions based on current flow state.

**Parameters:**

- `repo_path` (string): Path to the Git repository

**Returns:**

```json
{
  "recommendations": [
    "Consider making a checkpoint commit to save your progress."
  ]
}
```

### `set_rules`

Dynamically update configuration thresholds.

**Parameters:**

- `config` (object): Configuration values to update

## Development

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/flowcheck --cov-report=term-missing
```

## License

MIT
