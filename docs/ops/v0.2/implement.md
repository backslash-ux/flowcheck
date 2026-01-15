# v0.2 Implementation Roadmap

This document outlines the planned engineering work for FlowCheck v0.2, focusing on "Smart" features and Developer Experience (DX) improvements.

## 1. Smart Intent Layer (BYOK LLM)

**Goal**: Replace heuristic TF-IDF checks with LLM reasoning.

- [x] Create `LLMClient` abstraction in `src/flowcheck/llm/`.
- [x] Implement `OpenAIProvider` (via `OpenAIClient`).
- [ ] Implement `AnthropicProvider`, `GeminiProvider`. (Deferred)
- [x] Update `IntentValidator` to use `LLMClient` if configured.
- [x] Add prompt templates for "Scope Creep Detection" and "Missing Criteria".
- [x] **Crucial**: Ensure `Guardian` sanitizer runs on diffs _before_ sending to LLM.

## 2. Configuration & DX

**Goal**: Reduce friction for teams and power users.

- [x] **Project-level Config**: Look for `.flowcheck.json` in git root and merge with `~/.flowcheck/config.json`.
- [x] **Ignore Support**: Parse `.flowcheckignore` (glob patterns) to exclude files from analysis (e.g., `tests/fixtures/`).
- [ ] **CLI Configurator**: `flowcheck setup` command to interactively set API keys and paths.

## 3. Enhanced Observability

**Goal**: Deeper insight into "Why did the agent do that?"

- [ ] Log LLM Verdicts: Record the "Why" reasoning from the Smart Intent layer into `audit.log`.
- [ ] Token Usage Tracking: Track cost/tokens for the BYOK integration.

## 4. Migration Plan

1. **Backwards Compatibility**: v0.1 config must continue to work.
2. **Feature Flags**: New features (LLM Intent) are opt-in.
3. **Docs**: Update `README.md` with "Cloud Integration" section.

## 5. Future (v0.3+)

- **Local LLM Support**: Re-visit Ollama/Llamafile if users demand offline "Smart" checks.
- **RAG for History**: Use the LLM to query the `search_history` vector store for "Contextual Q&A" (e.g., "Why was this variable added 3 months ago?").
