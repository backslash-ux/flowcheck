# FlowCheck Rules for AI Agents

> **This file instructs AI agents to enforce Git hygiene during agentic coding sessions.**

## FlowCheck MCP Tools

You are given tools from the FlowCheck MCP server for maintaining Git hygiene. You `MUST` follow these rules:

## 1. `get_flow_state`

You `MUST` call this tool:

- **Before starting any new task** to assess current repository health
- **Before making commits** to understand the scope of changes
- **Periodically during long coding sessions** (every 15-20 tool calls)
- **When resuming work** on a repository after any interruption

## 2. `get_recommendations`

You `MUST` call this tool:

- **When `get_flow_state` returns status `warning` or `danger`**
- **Before proposing large refactors** to check if changes should be split
- **At the end of each major task** to ensure clean commit hygiene
- **When uncommitted lines exceed 300** to get guidance on splitting work

## 3. `set_rules`

You `MAY` call this tool when:

- The user explicitly requests different thresholds
- Working on a codebase with specific commit policies

## Enforcement Behavior

When FlowCheck reports `warning` or `danger` status, you `MUST`:

1. **Pause new feature work** and address the hygiene issue first
2. **Suggest a checkpoint commit** if time threshold is exceeded
3. **Propose splitting changes** if line count threshold is exceeded
4. **Inform the user** of the flow health status and your recommendation

## Example Integration

```
Before starting work:
1. Call get_flow_state(repo_path)
2. If status is not "ok", call get_recommendations(repo_path)
3. Address any hygiene issues before proceeding
4. Begin the requested task
```

## Philosophy

FlowCheck is a "smart fitness watch" for coding—it nudges, never blocks. But as an AI agent, you should treat these nudges as **strong recommendations** to maintain a clean, reviewable Git history that humans can easily understand and audit.
