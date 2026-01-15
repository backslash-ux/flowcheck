# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-01-15

### Added

- **Docker Containerization**: Production-ready Docker deployment
  - 3 image variants: production, slim (~120MB), development
  - Multi-stage builds for layer optimization
  - Non-root container security (UID 999)
  - Process-based health checks
- **Docker Compose**: One-command deployment stacks
  - Production stack with volume persistence
  - Development stack with hot-reload
- **GitHub Actions CI/CD**: Automated multi-arch builds (amd64/arm64)
- **Deployment Guides**: Comprehensive documentation
  - Docker setup and configuration
  - Kubernetes manifests
  - CI/CD integration (GitHub Actions, GitLab CI, Jenkins)
  - Troubleshooting guide

### Changed

- Reports consolidated to `docs/` folder for public availability
- Updated documentation with Docker deployment options

## [0.3.0] - 2026-01-10

### Added

- **CLI Enforcement**: Actionable commands for Git hygiene
  - `flowcheck check [--strict]` - Health check with security scanning
  - `flowcheck index [--incremental]` - Semantic commit indexing
  - `flowcheck install-hooks` - Pre/post-commit hook installation
- **Git Hooks**: Automatic enforcement via pre-commit/post-commit
  - Pre-commit blocks commits with secrets/PII
  - Post-commit auto-indexes new commits
- **Strict Mode**: Exit codes (0=ok, 1=warning, 2=security)
- **Session Management**: MCP session lifecycle and audit correlation

### Changed

- Improved TF-IDF vectorization with vocabulary persistence
- Enhanced SQLite backend for semantic search

## [0.2.0] - 2026-01-05

### Added

- **Smart Intent Verification**: BYOK LLM integration for ticket alignment
  - Anthropic Claude support
  - OpenAI GPT-4 support
  - Fallback to TF-IDF when LLM unavailable
- **Configuration**: Hierarchical config (repo > global > defaults)
  - `.flowcheck.json` for repo-level settings
  - `.flowcheckignore` for file exclusions

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
