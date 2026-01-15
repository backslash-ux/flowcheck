# v0.3 Implementation Roadmap: "Make It Enforceable"

> **Status**: ✅ **RELEASED** as `v0.3.0` on January 15, 2026  
> **Branch**: `release/v0.3` | **Tag**: `v0.3.0`  
> **Tests**: 136/136 passing (100%)

This document outlines the engineering work for FlowCheck v0.3, focusing on **enforcement**, **automation**, and **developer experience**.

## Goals

v0.3 transforms FlowCheck from a "passive observer" into an "active co-pilot" that:

1. **Enforces** security policies via pre-commit hooks
2. **Automates** commit indexing for semantic search
3. **Expands** LLM support beyond OpenAI
4. **Improves** DX with CLI tooling and session management

---

## 1. CLI Foundation ✅

**Goal**: Provide command-line interface for setup, indexing, and health checks.

### 1.1 CLI Entry Point

Created `src/flowcheck/cli.py` with subcommands:

```bash
flowcheck check [repo_path]     # Run health check + security scan
flowcheck index [repo_path]     # Index commit history for semantic search
flowcheck setup                 # Interactive configuration wizard
flowcheck install-hooks         # Install pre-commit hooks
```

### 1.2 Tasks

- [x] Create `cli.py` with argparse/click foundation
- [x] Implement `check` subcommand (wraps get_flow_state)
- [x] Implement `index` subcommand (triggers CommitIndexer)
- [x] Implement `install-hooks` subcommand
- [ ] Implement `setup` wizard (deferred to v0.3.1)
- [x] Add `flowcheck` CLI entry point to `pyproject.toml`

---

## 2. Pre-Commit Hook Integration ✅

**Goal**: Actually BLOCK dangerous commits with secrets/PII.

### 2.1 Hook Generator

Created `src/flowcheck/hooks/installer.py`:

- Generates a `.git/hooks/pre-commit` script
- Script calls `flowcheck check --strict` and blocks on non-zero exit
- Supports `--force` bypass with audit logging

### 2.2 Strict Mode

Add `--strict` flag to `flowcheck check`:

- Exit code 0: All clear
- Exit code 1: Warnings present (non-blocking by default)
- Exit code 2: Security flags detected (always blocks)

### 2.3 Tasks

- [x] Create `hooks/` module with hook templates
- [x] Implement `install-hooks` command
- [x] Add `--strict` flag to check command
- [x] Audit log bypass attempts (`--force`)

---

## 3. Automatic Commit Indexing ✅

**Goal**: Keep semantic search index up-to-date automatically.

### 3.1 Post-Commit Hook

Added optional `post-commit` hook that:

- Indexes the new commit immediately
- Runs in background (non-blocking)
- Gracefully handles errors

### 3.2 Incremental Indexing

Enhance `CommitIndexer`:

- Track last indexed commit hash
- Only index new commits since last run
- Persist vectorizer vocabulary

### 3.3 Tasks

- [x] Add `index_single_commit()` method to indexer
- [x] Add `get_last_indexed_hash()` tracking
- [x] Create `post-commit` hook template
- [x] Add `--incremental` flag to `flowcheck index`

---

## 4. Anthropic LLM Provider ✅

**Goal**: Support Claude models for Smart Intent verification.

### 4.1 AnthropicClient

Created `src/flowcheck/llm/anthropic_client.py`:

- Implements `LLMClient` abstract interface
- Uses Messages API with JSON mode
- Handles rate limits gracefully

### 4.2 Configuration

```json
{
  "intent": {
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514",
    "api_key_env": "ANTHROPIC_API_KEY"
  }
}
```

### 4.3 Tasks

- [x] Create `AnthropicClient` class
- [x] Update `get_llm_client()` factory
- [x] Add tests for Anthropic provider
- [x] Document in README

---

## 5. Session & Trace Management ✅

**Goal**: Correlate tool calls across an agent session.

### 5.1 Session Context

Added `session_id` that persists across MCP tool calls:

- Generated on first tool call or via `start_session()` tool
- Included in all audit log entries
- Exposed via `get_session_info()` tool

### 5.2 MCP Tools

```python
@mcp.tool
def start_session(agent_id: str = "") -> dict:
    """Start a new FlowCheck session for audit correlation."""

@mcp.tool  
def get_session_info() -> dict:
    """Get current session ID and statistics."""
```

### 5.3 Tasks

- [x] Create `SessionManager` class
- [x] Add session context to audit logger
- [x] Implement `start_session` tool
- [x] Implement `get_session_info` tool
- [x] Wire session ID through existing tools

---

## 6. Enhanced Audit Logging ✅

**Goal**: Better observability for production use.

### 6.1 Improvements

- Include session_id in all entries
- Log LLM verdicts and reasoning
- Track tool call durations
- Add log rotation (max 10MB per file)

### 6.2 Tasks

- [x] Add session_id to AuditEntry
- [x] Add timing metadata
- [x] Implement log rotation
- [ ] Add LLM verdict logging (via intent layer)

---

## 7. Testing & Documentation ✅

### 7.1 Tests

- [x] CLI unit tests
- [x] Hook installation tests
- [x] Incremental indexing tests
- [x] Anthropic client mock tests
- [x] Session management tests

### 7.2 Documentation

- [x] Update README with CLI usage
- [x] Add "Installation" guide with hook setup
- [x] Document Anthropic configuration
- [x] Add troubleshooting section

---

## Bug Fixes

### Vector Persistence Fix (CRITICAL)

**Issue**: Semantic search returned empty results after initial indexing because vectors were stored as NULL in the database.

**Root Cause**: 
- `index_incremental()` called `index_single_commit()` which skipped vectorization when `vectorizer._fitted=False`
- `index_repo()` always called `fit()`, overwriting existing vocabulary on re-runs

**Solution** (commit `f5be723`):
1. `index_repo()`: Check `if not self.vectorizer._fitted` before fitting
2. `index_incremental()`: Fit vectorizer on first batch when not already fitted

**Verification**: E2E test confirmed search returns results with score 0.76+

---

## Migration Notes

1. **Backwards Compatibility**: All v0.2 configs continue to work
2. **Opt-in Hooks**: Hooks are not installed by default
3. **Graceful Degradation**: If Anthropic API fails, falls back to OpenAI, then TF-IDF

---

## File Structure (New/Modified)

```
src/flowcheck/
├── cli.py                    # NEW: CLI entry point
├── hooks/
│   ├── __init__.py           # NEW
│   ├── installer.py          # NEW: Hook installation logic
│   └── templates.py          # NEW: Hook script templates
├── llm/
│   ├── anthropic_client.py   # NEW: Anthropic provider
│   └── client.py             # MODIFIED: factory update
├── semantic/
│   └── indexer.py            # MODIFIED: incremental indexing
├── session/
│   ├── __init__.py           # NEW
│   └── manager.py            # NEW: Session management
├── telemetry/
│   └── audit_logger.py       # MODIFIED: session + rotation
└── server.py                 # MODIFIED: session tools
```

---

## Timeline

| Phase | Features | Estimate | Status |
|-------|----------|----------|--------|
| Phase 1 | CLI + Strict Mode | 2-3 hours | ✅ Complete |
| Phase 2 | Hooks + Indexing | 2-3 hours | ✅ Complete |
| Phase 3 | Anthropic Client | 1-2 hours | ✅ Complete |
| Phase 4 | Session Management | 1-2 hours | ✅ Complete |
| Phase 5 | Tests + Docs | 2 hours | ✅ Complete |
| Phase 6 | Bug Fixes & Release | 1 hour | ✅ Complete |

---

## Release Notes (v0.3.0)

**Released**: January 15, 2026

### Highlights

- 🛡️ **Pre-commit hooks** block dangerous commits with `--strict` mode
- 🔄 **Post-commit hooks** auto-index new commits for semantic search  
- 🤖 **Anthropic Claude** support for Smart Intent verification
- 🔗 **Session management** correlates tool calls across agent sessions
- 📊 **136 tests** passing with 100% coverage of new features

### Deferred to v0.3.1

- `flowcheck setup` wizard for interactive configuration
- LLM verdict logging via intent layer

### Breaking Changes

None. Full backwards compatibility with v0.2 configs.

**Total**: ~10 hours of engineering work
