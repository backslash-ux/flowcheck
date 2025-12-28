# FlowCheck MCP Safety Layer: v0 Technical Specification

## 1.0 Introduction and Core Concepts

The FlowCheck MCP Safety Layer is a local agent designed to enhance developer productivity by providing gentle, configurable guardrails. It operates as a non-blocking "safety layer" or "flow coach" that observes local development behavior and surfaces helpful suggestions. Unlike traditional tools that act as a "traffic cop" by enforcing policy and blocking actions, FlowCheck is designed to be a "smart fitness watch" for coding. It preserves a developer's momentum while providing quiet, data-driven feedback to encourage safer, more maintainable habits. This document specifies the v0 implementation of the FlowCheck system for developers and integrators.

The core concept of FlowCheck is to function as a Model Context Protocol (MCP) server that exposes "flow health" data and suggestions to compatible clients, such as code editors, terminals, or local dashboards. Its primary functions can be summarized as follows:

- **Observe**: It monitors local development signals, with an initial focus on Git repository activity.
- **Derive**: It processes these raw signals into higher-level, meaningful metrics that describe the developer's current "flow health," such as the time elapsed since the last commit or the size of the uncommitted changes.
- **Expose**: It makes this derived data and a set of actionable recommendations available through a clean, RPC-style MCP server interface for consumption by various client tools.

This "safety layer" philosophy is central to FlowCheck's design. The system is explicitly intended to guide, not to restrict. As noted in the design documents, "It does not block; it nudges." For example, instead of preventing work on a large set of changes, it might surface a suggestion like, "This branch diff is huge; consider a checkpoint or split." This approach respects the developer's workflow while gently encouraging practices that reduce future friction, such as avoiding "merge hell" or creating a more readable version history.

This specification details the system architecture, data model, and API that enable this coaching-oriented approach.

## 2.0 System Architecture (v0)

The v0 architecture for FlowCheck is designed to be modular, extensible, and local-first. This strategic design ensures that all data analysis remains on the user's machine, guaranteeing privacy and security. Furthermore, by exposing a clean MCP interface, it creates a clear separation of concerns, allowing a single backend engine to serve multiple surfaces—such as an editor plugin, a CLI client, a dashboard, or an AI agent—without modification.

### 2.1 Core Components

The v0 architecture is comprised of four primary components that work in concert to deliver the FlowCheck service.

1. **Core Engine (Python)**: This is the backend logic, wrapping the Git CLI or libraries like gitpython, responsible for inspecting repositories and calculating raw metrics like commit timestamps and diff statistics.
2. **Rules Engine**: This component contains a set of simple Python functions that map the quantitative metrics from the `flow_state` object to qualitative, human-readable suggestions based on user configuration.
3. **Guardian Layer**: A security-focused component responsible for scanning diffs and content for PII, secrets, and prompt injection attempts before they leave the local environment.
4. **Intent Layer**: A verification component that cross-references local code changes with external task definitions (e.g., GitHub Issues) to detect scope creep and ensure alignment.
5. **MCP Server**: This is a wrapper around the engine that exposes the system's data and recommendations via standard MCP tools.
6. **Configuration**: A local file that defines the user-specific thresholds that trigger warnings and suggestions.

### 2.2 Data Flow

The logical flow of data through the system begins with the Core Engine, which actively observes a target Git repository. It extracts low-level signals, such as the timestamp of the last commit and diff statistics. This raw data is then processed to derive a structured `flow_state` object containing metrics like `minutes_since_last_commit`. The Rules Engine evaluates this `flow_state` object against thresholds defined in the Configuration file to generate a list of actionable recommendations. Finally, the MCP Server exposes both the raw `flow_state` and the generated recommendations to any connected MCP-compliant client.

This architectural overview provides the foundation for the specific data signals the system will process and expose.

## 3.0 Data Model Specification

The effectiveness of FlowCheck is rooted in its ability to transform low-level, raw development signals into a high-level, actionable `flow_state`. This data model is the core of the system, providing the quantitative basis for all qualitative recommendations.

### 3.1 Input Signals

The v0 implementation of the Core Engine will observe the following raw signals from the local development environment.

| Signal Source | Specific Data Point          | Description                                                                     |
| ------------- | ---------------------------- | ------------------------------------------------------------------------------- |
| Git           | Current branch               | The name of the currently active Git branch.                                    |
| Git           | Time since last commit       | The duration since the last commit was made in the current branch.              |
| Git           | Number of changed files      | The count of files that have been modified but not yet committed.               |
| Git           | Total added/removed lines    | A sum of line additions and deletions in the uncommitted diff.                  |
| Session       | System idle time             | Optional: The duration of system inactivity or time since last keyboard input.  |
| Integration   | `ticket_id`                  | The ID of the task/issue currently being worked on (e.g., GitHub Issue ID).     |
| Security      | Scan Results                 | Boolean flags for `pii_detected`, `secrets_detected`, and `injection_detected`. |
| Config        | `max_minutes_without_commit` | A user-defined threshold for the maximum minutes before a nudge.                |
| Config        | `max_lines_uncommitted`      | A user-defined threshold for the maximum uncommitted lines before a nudge.      |

### 3.2 Derived State Object: `flow_state`

The Core Engine processes the input signals to produce a single, coherent `flow_state` object. This object represents the canonical "flow health" of the observed repository at a given moment.

| Field                       | Data Type    | Description                                                                                                  |
| --------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------ |
| `minutes_since_last_commit` | Integer      | The number of minutes that have passed since the last commit.                                                |
| `uncommitted_lines`         | Integer      | The total number of lines added and removed in the current diff.                                             |
| `uncommitted_files`         | Integer      | The total number of files with uncommitted changes.                                                          |
| `branch_name`               | String       | The name of the current Git branch.                                                                          |
| `status`                    | Enum         | A qualitative indicator of flow health. Possible values are `"ok"` \| `"warning"` \| `"danger"`.             |
| `security_flags`            | List[String] | A list of warnings regarding detected secrets, PII, or injection attempts (e.g., `["⚠️ SECRETS detected"]`). |

**Note on Future Capabilities**: The architecture is designed to accommodate additional derived metrics in future versions. Optional fields planned for inclusion include `branch_age_days` and `behind_main_by_commits` to enable more advanced branch hygiene rules.

This clearly defined data model provides the structured output that is exposed via the system's API.

## 4.0 Configuration Specification

Configuration is a key element of FlowCheck's design, making it a personal and non-intrusive tool. By allowing developers to define their own thresholds, the system's nudges can be aligned with an individual's personal workflow and tolerance, a concept referred to as "vibe coding." This configurability is core to the philosophy that FlowCheck is a "lightweight and personal" tool, not a "team policy engine," ensuring it remains a helpful coach rather than a source of unwanted noise.

The system's configuration is managed via a local JSON file. The default location for this file is `~/.flowcheck/config.json`.

The v0 implementation supports the configuration of the following core thresholds, which are used by the Rules Engine to determine when to generate suggestions.

| Parameter                    | Data Type | Description                                                                                |
| ---------------------------- | --------- | ------------------------------------------------------------------------------------------ |
| `max_minutes_without_commit` | Integer   | The number of minutes a developer can work without a commit before a warning is triggered. |
| `max_lines_uncommitted`      | Integer   | The maximum size of an uncommitted diff (in lines) before a warning is triggered.          |

This configuration directly governs the behavior of the system, which is exposed through the following precise API contract.

## 5.0 API Specification: MCP Tools (v0)

The Model Context Protocol (MCP) tool interface is the primary contract between the FlowCheck server and all consuming clients, including code editors, AI agents, and dashboards. The API is intentionally designed as a clean, RPC-style interface with no assumptions about the client's user interface, ensuring broad compatibility and extensibility for a rich ecosystem of tools.

### 5.1 Tool: `get_flow_state`

**Purpose**: Returns the current derived metrics (`flow_state` object) for a given repository. This allows clients, particularly AI agents, to understand the developer's current context without requiring manual explanation.

**Parameters**:

| Parameter   | Type   | Description                                          |
| ----------- | ------ | ---------------------------------------------------- |
| `repo_path` | String | The absolute or relative path to the Git repository. |

**Return Value**: A JSON object representing the current `flow_state`.

### 5.2 Tool: `get_recommendations`

**Purpose**: Returns an array of human-readable 'nudges' generated by the Rules Engine, providing actionable suggestions to the user based on the current context.

**Parameters**:

| Parameter   | Type   | Description                                          |
| ----------- | ------ | ---------------------------------------------------- |
| `repo_path` | String | The absolute or relative path to the Git repository. |

**Return Value**: A JSON object containing a `recommendations` key, which holds an array of string-based suggestions.

### 5.3 Tool: `set_rules` (Optional)

**Purpose**: An optional tool for dynamically updating configuration thresholds, either globally or on a per-repository basis.

**Parameters**: The tool accepts a `config` object. The precise schema for this object is out of scope for the v0 specification but conceptually allows clients to modify the rule thresholds used by the engine.

This API provides a simple yet powerful foundation for building a wide range of practical applications on top of the FlowCheck safety layer.

### 5.4 Tool: `search_history`

**Purpose**: Performs a semantic search over the commit history using embedding-based retrieval (if available) or keyword search, allowing users to find "concepts" rather than just exact strings.

**Parameters**:

| Parameter   | Type    | Description                                                |
| ----------- | ------- | ---------------------------------------------------------- |
| `query`     | String  | The natural language search query (e.g., "auth refactor"). |
| `repo_path` | String  | Path to the repository.                                    |
| `top_k`     | Integer | (Optional) Number of results to return. Default: 5.        |

**Return Value**: JSON object containing a list of matched commits with their metadata and relevance scores.

### 5.5 Tool: `verify_intent`

**Purpose**: Validates that the current uncommitted changes align with the stated goal of a specific ticket or issue. It acts as a check against scope creep.

**Parameters**:

| Parameter   | Type   | Description                                                                        |
| ----------- | ------ | ---------------------------------------------------------------------------------- |
| `ticket_id` | String | The identifier of the issue (e.g., GitHub Issue number).                           |
| `repo_path` | String | Path to the repository.                                                            |
| `context`   | String | (Optional) User-provided context or description of what they think they are doing. |

**Return Value**: JSON object containing an `alignment_score` (0-1) and a list of warnings if the work appears unrelated to the ticket.

### 5.6 Tool: `sanitize_content`

**Purpose**: A utility for clients to redact sensitive information (secrets, PII) from text content _before_ sending it to an LLM or sharing it.

**Parameters**:

| Parameter | Type   | Description                       |
| --------- | ------ | --------------------------------- |
| `content` | String | The raw text content to sanitize. |

**Return Value**: JSON object containing the `sanitized_text` and flags indicating what was redacted.

## 6.0 Rule Engine Logic (v0)

The Rules Engine is the component that translates the quantitative data from the `flow_state` object into qualitative, actionable suggestions for the developer. It acts as the "brain" of the flow coach, determining when and how to provide helpful nudges based on the configured thresholds.

### 6.1 Core Hygiene Rules

The initial v0 implementation will focus on a small but meaningful set of rules related to "Commit hygiene." These rules are designed to encourage small, frequent commits, which improves repository history and simplifies code review.

#### Time-based Commit Nudge

- **Condition**: If `minutes_since_last_commit` is greater than the configured `max_minutes_without_commit` threshold (N).
- **Action**: Suggest that the user create a "checkpoint commit" to save their progress.

#### Diff-size-based Commit Nudge

- **Condition**: If `uncommitted_lines` is greater than the configured `max_lines_uncommitted` threshold (M).
- **Action**: Suggest that the user consider splitting the work into smaller, more focused commits or branches.

### 6.2 Future Rule Considerations

While out of scope for v0, the architecture is designed to accommodate a richer set of rules in the future. These provide context for the system's intended evolution.

- **Branch Hygiene**: Rules could be added to detect when a branch is stale (e.g., `branch_age_days > Y`) or has fallen significantly behind the main branch (`behind_main_by_commits > X`), prompting a suggestion to merge or rebase to avoid painful conflicts.
- **Session Sanity**: More advanced heuristics could detect "context thrashing," such as frequent branch switching in a short period of time, and provide hints to help the developer regain focus.

This specification provides a complete blueprint for building the v0 implementation of the FlowCheck MCP server, establishing a robust, privacy-first foundation for a new class of local, context-aware developer productivity tools.
