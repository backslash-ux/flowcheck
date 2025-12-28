# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-12-28

### Added

- **Guardian Layer**: Security proxy that scans for PII, secrets, and prompt injection attacks.
  - `sanitize_content` tool for manual redaction.
  - Automatic scanning in `get_flow_state` and `get_recommendations`.
- **Semantic Layer**:
  - `search_history` tool for finding commits by meaning (TF-IDF vector search).
  - Local SQLite-based indexer for commit history.
- **Intent Layer**:
  - `verify_intent` tool with GitHub Issues integration.
  - Automatic scope creep detection (comparing issue requirements vs. diff).
- **Observability**:
  - OpenTelemetry tracing with `gen_ai` semantic conventions.
  - Local append-only audit log at `~/.flowcheck/audit.log`.
- **Core**:
  - `security_flags` field in `FlowState`.
  - `branch_age_days` and `behind_main_by_commits` metrics.

### Changed

- **Server**: Fully rewritten `FastMCP` server integration to support new v0.1 architecture.
- **Docs**: Comprehensive update to README, Agent Rules, and Ops documentation.

### Security

- Added `security_flags` to warn agents about potential leaks or injection risks before they commit.
