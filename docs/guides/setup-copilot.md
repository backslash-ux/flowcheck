# Setting up FlowCheck with GitHub Copilot (VS Code)

GitHub Copilot in VS Code now supports the Model Context Protocol (MCP), allowing it to use local tools like FlowCheck to analyze your code and provide context-aware suggestions.

## Prerequisites

- **VS Code** (Latest version recommended)
- **GitHub Copilot Extension** installed and active
- **FlowCheck** installed locally (see [README](../../README.md))

## 1. Register FlowCheck via CLI

The easiest way to add FlowCheck to Copilot is using the VS Code command-line interface.

1. Open your terminal.
2. Run the following command (adjusting paths to match your system):

   ```bash
   code --add-mcp '{"name":"flowcheck","command": "/ABSOLUTE/PATH/TO/flowcheck/.venv/bin/python", "args": ["-m", "flowcheck.server"]}'
   ```

   **Breakdown:**

   - `command`: The absolute path to the python executable in your FlowCheck virtual environment.
   - `args`: The module to run (`-m flowcheck.server`).

   > **Tip**: Run `which python` inside your FlowCheck project folder to get the correct path.

## 2. Configure via `.vscode/mcp.json` (Workspace Specific)

Alternatively, you can configure FlowCheck for a specific workspace by creating a configuration file.

1. Create a file named `.vscode/mcp.json` in your project root.
2. Add the following configuration:

   ```json
   {
     "servers": {
       "flowcheck": {
         "command": "/ABSOLUTE/PATH/TO/flowcheck/.venv/bin/python",
         "args": ["-m", "flowcheck.server"]
       }
     }
   }
   ```

## 3. Trusting the Server

When you first use FlowCheck with Copilot, VS Code will ask you to **Trust** the MCP server.

- Click **Trust** to allow FlowCheck to run and access your repository.
- You can manage trusted servers via the **MCP: Manage Trusted Servers** command in the Command Palette.

## 4. How to Use

Once registered, you can ask Copilot Chat to use FlowCheck tools.

### Health Check

> "Run `get_flow_state` to see if my branch is healthy."

### Security Scan (Before Committing)

> "Check `get_recommendations`. Are there any security flags I should fix?"

### Contextual Search

> "Use `search_history` to find why we added the timeout to the API client."

## Troubleshooting

- **"Tool not found"**: Ensure you restarted VS Code after adding the server.
- **"Connection Refused"**: Check the Output panel for "GitHub Copilot" or "MCP" to see if the python process failed to start (usually a path issue).
