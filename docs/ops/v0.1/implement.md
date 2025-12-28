# FlowCheck: Production-Grade Implementation Plan (v1)

## 1. Executive Summary

FlowCheck is a local "safety layer" designed to resolve the paradox between "vibe coding" (deep creative focus) and development hygiene/security. It operates as a Model Context Protocol (**MCP**) server that observes local development signals to derive "flow health" metrics.

Unlike traditional linters that block actions, FlowCheck acts as a "smart fitness watch" for AI-assisted development. It provides non-blocking nudges for hygiene (commit size, branch age) while actively sanitizing data to prevent security threats like indirect prompt injection. It is architected to be privacy-first, keeping analysis local, while emitting standardized telemetry for enterprise auditability.

## 2. System Architecture: The "Defense-in-Depth" Model

To address the "semantic gap" and security risks identified in recent MCP research, FlowCheck adopts a layered architecture. It separates raw data retrieval from agent exposure via a sanitization proxy.

### 2.1 Architectural Layers

1.  **The Observer Layer (Core Engine)**:
    - **Function**: Wraps Git CLI and file system watchers to gather raw signals (diffs, timestamps, file stats).
    - **New Capability**: Local Vector Indexer. Uses `tree-sitter` to chunk code and a local vector store (e.g., SQLite/Qdrant) to embed commit history for semantic search.
2.  **The Guardian Layer (Security Proxy)**:
    - **Function**: Intercepts raw data before it reaches the Rules Engine or MCP Server.
    - **Component**: Sanitizer Proxy. Scans diffs and logs for PII (Personally Identifiable Information) and secrets using regex and NER (Named Entity Recognition) models. It replaces sensitive data with tokens (e.g., `[REDACTED_API_KEY]`).
    - **Component**: Prompt Injection Filter. Analyzes diff text for adversarial instructions (e.g., "Ignore previous rules") using a classifier.
3.  **The Logic Layer (Rules & Context)**:
    - **Function**: Derives `flow_state` and generates recommendations.
    - **Component**: Intent Validator. Connects to issue trackers (Jira/Linear) to compare the semantic intent of the ticket against the vector embeddings of the current diff.
4.  **The Interface Layer (MCP Server)**:
    - **Function**: Exposes sanitized data via JSON-RPC 2.0.
    - **Protocol**: Implements strict capability negotiation and standardizes error handling (400 vs 500 series errors).

## 3. Data Model Specification

The data model is expanded to support observability and security verification.

### 3.1 Derived State Object (`flow_state`)

The API returns a canonical object representing repository health.

| Field                  | Type    | Description                                                         | Source           |
| :--------------------- | :------ | :------------------------------------------------------------------ | :--------------- |
| `status`               | Enum    | Health indicator: `ok`, `warning`, `danger`.                        | Rules Engine     |
| `minutes_since_commit` | Integer | Time elapsed since HEAD commit.                                     | Git CLI          |
| `uncommitted_lines`    | Integer | Total additions/deletions in working tree.                          | Git CLI          |
| `rework_rate`          | Float   | % of code rewritten within 21 days (quality metric).                | History Index    |
| `ticket_alignment`     | Float   | Semantic similarity score (0.0-1.0) between active ticket and diff. | Intent Validator |
| `security_flags`       | Array   | List of redacted items or detected injection attempts.              | Guardian Layer   |

### 3.2 OpenTelemetry (OTel) Semantic Conventions

To solve the "black box" problem of autonomous agents, FlowCheck emits traces for every interaction using standard `gen_ai` attributes.

| Attribute Namespace  | Data Points                    | Purpose                                                            |
| :------------------- | :----------------------------- | :----------------------------------------------------------------- |
| `gen_ai.agent.id`    | Agent UUID, Model Version      | Tracks who (human or specific agent) requested the data.           |
| `gen_ai.action.type` | `tool_call`, `nudge_generated` | Distinguishes between passive observation and active intervention. |
| `gen_ai.safety.pii`  | Boolean (True/False)           | Flags if PII was detected and redacted in the response.            |
| `gen_ai.task.id`     | Jira/Linear Ticket ID          | Links the technical action to business intent.                     |

## 4. API Specification (MCP Tools)

The MCP server exposes tools designed for both human feedback and agent consumption.

### Tool 1: `get_flow_state`

- **Purpose**: Returns the raw `flow_state` object.
- **Security**: Output is passed through the Sanitizer Proxy to redact secrets/PII before return.

### Tool 2: `get_recommendations`

- **Purpose**: Returns actionable nudges based on heuristics and semantic analysis.
- **Logic**:
  - **Heuristic**: "90 mins since last commit."
  - **Semantic**: "Your diff includes database schema changes not mentioned in linked ticket PROJ-123 (Intent Mismatch)."
  - **Safety**: "Diff contains potential prompt injection pattern; commit blocked until manual review."

### Tool 3: `verify_intent` (New)

- **Purpose**: Validates the current work against a specific requirement.
- **Parameters**: `{ "ticket_id": "string", "context": "string" }`
- **Mechanism**: Fetches ticket criteria, embeds them, and calculates cosine similarity against the current git diff embeddings.
- **Returns**: `{"alignment_score": 0.85, "missing_criteria": ["Edge case handling for null inputs"]}`.

### Tool 4: `search_history_semantically` (New)

- **Purpose**: Allows agents to find context by "meaning" rather than keyword grep.
- **Parameters**: `{ "query": "string" }`
- **Mechanism**: Queries the local vector index (Qdrant/SQLite) for similar past commits/diffs.
- **Use Case**: "Find how we handled API retries in the past" returns relevant commits even if the word "retry" is missing but "exponential backoff" is present.

## 5. Security & Governance Implementation

This section details the specific controls required to make FlowCheck "Production-Grade."

### 5.1 Input/Output Sanitization (The "Air Gap")

- **Requirement**: FlowCheck must not trust the LLM with raw data.
- **Implementation**: Integrate `llm-guard` or Presidio libraries.
  - **Pre-processing**: Before analyzing a diff for recommendations, strip high-entropy strings (secrets) and known PII patterns.
  - **Post-processing**: Scan generated recommendations to ensure they do not hallucinate secrets back into existence (Deanonymization check).

### 5.2 Immutable Audit Trails

- **Requirement**: SOC 2 compliance requires a "gap-free sequence of events."
- **Implementation**:
  - Every tool invocation creates a log entry with a unique `trace_id`.
  - Logs are stored in a local append-only file (WORM storage simulation) or shipped to a centralized collector (e.g., Splunk/ELK) if in enterprise mode.
  - **Log Format**: `[Timestamp] [Agent_ID] [Action] [Risk_Score] [Sanitized_Payload]`

### 5.3 Permission Scoping (Least Privilege)

- **Requirement**: Prevent "Confused Deputy" attacks where an agent is tricked into destructive actions.
- **Implementation**:
  - **Read-Only Default**: FlowCheck defaults to `git log`, `git status`, `git diff`.
  - **Human-in-the-Loop (HITL)**: Any write operation (e.g., `git commit` initiated by an agent) requires explicit user confirmation via the host UI.

## 6. Roadmap: Phased Rollout

### Phase 1: Visibility & Hygiene (The Fitness Watch)

- **Deliverables**:
  - Core Engine (Python) with Git CLI integration.
  - Basic MCP Server (`get_flow_state`, `get_recommendations`).
  - Configuration file (`~/.flowcheck/config.json`) for thresholds.
  - **Security**: Basic regex-based secret scanning (Gitleaks integration).

### Phase 2: The Semantic Layer (The Context Coach)

- **Deliverables**:
  - Local Vector Indexer: Background process using tree-sitter to chunk and index repo history.
  - Intent Validator: Integration with Jira/Linear APIs to fetch ticket context.
  - **Security**: Implementation of `llm-guard` for PII redaction and Prompt Injection detection.

### Phase 3: Enterprise Governance (The Safety System)

- **Deliverables**:
  - OTel Instrumentation: Full `gen_ai` tracing implementation.
  - Audit Logger: Immutable, structured logging for compliance.
  - Policy Engine: Allowlisting specific MCP servers and enforcing "no PII" rules.

## 7. Developer/Agent Usage Instructions

### For Developers

1.  **Install**: `pip install flowcheck-mcp`
2.  **Configure**: Edit `~/.flowcheck/config.json` to set your "vibe" thresholds (e.g., `max_uncommitted_lines: 500`).
3.  **Connect**: Add FlowCheck to your Cursor/Claude `mcp_config.json`.

### For AI Agents (System Prompt Instruction)

> "You are connected to the FlowCheck MCP server. Before generating code or suggesting commits, you MUST:
>
> 1. Call `get_flow_state` to check the current repository health.
> 2. If status is 'warning' or 'danger', prioritize cleanup tasks (committing, splitting diffs) over new feature work.
> 3. If you need historical context, use `search_history_semantically` instead of `git log`.
> 4. Do not include any data flagged in `security_flags` in your final output."

---

**Analogy for Understanding**: Think of FlowCheck not just as a fitness watch that tracks your heart rate (lines of code), but one equipped with a biometric payment lock. It helps you run faster (coding flow), but if it detects your pulse is irregular (context thrashing) or someone else is trying to use it (prompt injection), it locks the wallet (prevents commits/pushes) until you verify it's really you.
