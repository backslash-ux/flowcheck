# Setting up FlowCheck with Cursor

Cursor is an AI-first code editor that pairs perfectly with FlowCheck. By integrating FlowCheck as an MCP server, you give Cursor's AI real-time awareness of your project's health and security status.

## Prerequisites

- [Cursor](https://cursor.sh/) installed
- FlowCheck installed locally (see [README](../../README.md))

## 1. Add MCP Server Command

1. Open Cursor Settings (`Cmd + ,` or `Ctrl + ,`).
2. Navigate to **Features** -> **MCP**.
3. Click **+ Add New MCP Server**.
4. Enter the following details:

   - **Name**: `flowcheck`
   - **Type**: `command`
   - **Command**: Absolute path to your python executable in the virtual environment.
   - **Args**: `-m flowcheck.server`

   **Example**:

   ```bash
   # Command
   /path/to/flowcheck/.venv/bin/python

   # Args
   -m flowcheck.server
   ```

   > **Tip**: You can find the absolute path by running `which python` inside your active FlowCheck virtual environment.

5. Click **Save** and verify the status indicator turns green.

## 2. Configure Agent Rules

To make Cursor's AI "FlowCheck-aware", you should add a rule file that instructs it on how and when to use the tools.

1. Create a file named `.cursor/rules/flowcheck.mdc` in your project root.
2. Paste the contents of [`rules/flowcheck-rules.md`](../../rules/flowcheck-rules.md) into it.

This ensures that every time you start a chat or use Composer, Cursor knows to:

- Check `get_flow_state` before high-risk actions.
- Respect `security_flags`.
- Use `search_history` for context.

## 3. Workflow Example

1. **Start a Task**:

   > "I want to refactor the auth module. @flowcheck get_flow_state"

   Cursor will run the tool and see if you have uncommitted changes or security flags.

2. **Mid-Task Check**:

   > "I've been coding for a while. @flowcheck get_recommendations"

   Cursor will suggest if it's time to commit or split your work.

3. **Verify Intent**:

   > "I'm done with the auth fix. @flowcheck verify_intent ticket_id='102'"

   Cursor will use FlowCheck to verify if your code matches the ticket requirements.
