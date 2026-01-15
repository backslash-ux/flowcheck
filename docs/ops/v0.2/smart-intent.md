# Smart Intent Verification (Design Doc)

## 1. Problem Statement

In v0.1, FlowCheck uses TF-IDF (local vectorization) to compare GitHub Issues with local `git diff`s. While privacy-preserving and fast, this approach suffers from semantic rigidity:

- **False Positives**: "Refactoring DB" might not match "Improve Performance" keywords.
- **Lack of Nuance**: It cannot understand _implicit_ requirements or industry-standard implementation patterns.

## 2. Solution: BYOK LLM-as-a-Judge

Enable users to "Bring Your Own Key" (BYOK) to connect FlowCheck to powerful cloud LLMs (OpenAI, Anthropic, Gemini, DeepSeek) for a reasoning-based intent check.

### 2.1 Architecture

The `IntentValidator` class will be extended with an `LLMJudge` strategy.

```mermaid
graph LR
    User[Developer] -->|Verify Intent| FC[FlowCheck Server]
    FC -->|1. Fetch Issue| GitHub[GitHub API]
    FC -->|2. Read Diff| Git[Local Git]
    FC -->|3. Construct Prompt| Prompt[Prompt Engine]
    Prompt -->|4. Request| LLM[Cloud LLM (BYOK)]
    LLM -->|5. Verdict| FC
```

## 3. Configuration (BYOK)

Users configure their provider in `~/.flowcheck/config.json` or project-level `.flowcheck.json`.

```json
{
  "intent": {
    "provider": "openai",
    "model": "gpt-4o",
    "api_key_env": "OPENAI_API_KEY",
    "temperature": 0.1
  }
}
```

Support for:

- `openai` (GPT-4o, GPT-3.5-turbo)
- `anthropic` (Claude 3.5 Sonnet, Haiku)
- `gemini` (Gemini 1.5 Pro/Flash)
- `openrouter` (Any model)

## 4. Prompt Strategy

We do not send the _entire_ codebase. We send a constructed prompt with:

1.  **Task Context**: Release title, Issue Title, Issue Body.
2.  **Change Summary**: Result of `git diff --stat` and the first N lines of `git diff` (truncated to fit context/cost limits).
3.  **Rubric**:
    - IS_IN_SCOPE: (Yes/No)
    - SCOPE_CREEP_RISK: (Low/Medium/High)
    - EXPLANATION: Short reasoning.

### Example Prompt

```text
You are a Senior Technical Project Manager.
TASK: [Issue Title]
DETAILS: [Issue Body]

CHANGES DETECTED:
[Git Diff Summary]

VERDICT:
Does this code change directly address the task?
If there is extra work (refactoring, new features) not mentioned in the task, flag it as SCOPE CREEP.
Return JSON: { "aligned": bool, "scope_creep": bool, "reason": "string" }
```

## 5. Privacy & Security

- **Opt-In Only**: This feature is disabled by default. Users must explicitly configure a provider.
- **Data Minimization**: We only send the _diff_ and _issue_, not the full repo.
- **Sanitization**: The existing v0.1 `Guardian Layer` will run _before_ the prompt construction to ensure no secrets/PII are sent to the LLM provider.

## 6. Fallback Strategy

If:

1. No API key is present.
2. Network request fails.
3. User is offline.

The system automatically falls back to the v0.1 **TF-IDF Vectorizer** to ensure functionality is never broken.
