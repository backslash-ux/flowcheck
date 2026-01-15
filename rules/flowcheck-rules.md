# FlowCheck Rules for AI Agents

> **This file instructs AI agents to enforce Git hygiene and security during agentic coding sessions.**

## FlowCheck MCP Tools

You are given tools from the FlowCheck MCP server. You `MUST` follow these rules:

---

## 1. `get_flow_state` - Health Check

You `MUST` call this tool:

- **Before starting any new task** to assess repository health
- **Before making commits** to check for security flags
- **Periodically during long sessions** (every 15-20 tool calls)
- **When resuming work** after any interruption

**Critical**: If `security_flags` is non-empty, you `MUST NOT` proceed until issues are addressed.

---

## 2. `get_recommendations` - Actionable Guidance

You `MUST` call this tool:

- **When `get_flow_state` returns status `warning` or `danger`**
- **When `security_flags` contains any items**
- **Before proposing large refactors**
- **When uncommitted lines exceed 300**

---

## 3. `search_history` - Semantic Context

You `SHOULD` call this tool:

- **Before implementing features** to find similar past solutions
- **When debugging** to find how issues were fixed before
- **Instead of `git log`** when searching by concept, not keywords

Example: `search_history("authentication changes", repo_path)`

---

## 4. `verify_intent` - Smart Intent Validation

You `SHOULD` call this tool:

- **Before completing a task** to verify alignment with GitHub issue requirements
- **When scope seems to be expanding** beyond the original issue
- **Before large refactors** to confirm they're in scope

FlowCheck can use an **LLM Judge** (if configured) or heuristic analysis to detect scope creep.

Example: `verify_intent(ticket_id="42", repo_path=".")`

---

## 5. `sanitize_content` - Security Redaction

You `MUST` call this tool:

- **Before including file contents in outputs** if they may contain secrets
- **Before sharing code snippets** that haven't been security-scanned
- **When working with config files** that may contain credentials

---

## 6. `set_rules` - Configuration

You `MAY` call this tool when:

- The user explicitly requests different thresholds
- Working on a codebase with specific commit policies

---

## Enforcement Behavior

### When status is `warning` or `danger`:

1. **Pause new feature work** - address hygiene first
2. **Suggest checkpoint commit** if time threshold exceeded
3. **Propose splitting changes** if line count exceeded
4. **Inform the user** of flow health status

### When `security_flags` is non-empty:

1. **STOP** - do not proceed with commits
2. **Review** the flagged content for secrets/PII
3. **Use `sanitize_content`** to redact sensitive data
4. **Alert the user** about potential security issues

---

## Example Workflow

```
Before starting work:
1. Call get_flow_state(repo_path)
2. Check security_flags - if non-empty, address immediately
3. If status != "ok", call get_recommendations(repo_path)
4. Call search_history() for relevant context
5. Begin the requested task

Before completing work:
1. Call verify_intent(ticket_id, repo_path) if applicable
2. Call get_flow_state(repo_path) to verify clean state
3. Suggest commit with descriptive message
```

---

## Philosophy

FlowCheck is a "defense-in-depth" safety layer:

- **Hygiene nudges** keep commits small and reviewable
- **Security scanning** prevents accidental secret/PII leaks
- **Semantic search** reduces duplicate work and hallucinations
- **Intent validation** ensures code matches requirements

As an AI agent, treat FlowCheck warnings as **strong recommendations** to maintain a clean, secure, auditable Git history.
