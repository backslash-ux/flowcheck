# Using Smart Intent (AI Judge)

FlowCheck v0.2 introduces **Smart Intent Verification**, which uses an LLM (Large Language Model) to reason about your code changes. Instead of just matching keywords, the "AI Judge" reads your git diff and compares it against the semantic meaning of your ticket requirements.

## 1. Configuration (BYOK)

Smart Intent requires you to "Bring Your Own Key" (BYOK). Currently, we support OpenAI-compatible providers.

1. **Get an API Key** from OpenAI (or a compatible provider).
2. **Set the Environment Variable**:
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```
3. **Configure FlowCheck** in your project root (`.flowcheck.json`):

   ```json
   {
     "intent": {
       "provider": "openai",
       "model": "gpt-4o",
       "api_key_env": "OPENAI_API_KEY"
     }
   }
   ```

## 2. How it Works

When you run `verify_intent`, FlowCheck performs these steps:

1. **Sanitization**: Your git diff is scanned for PII/Secrets. Sensitive data is redacted effectively _before_ sending to the LLM.
2. **Context Assembly**: It gathers the ticket title/body (from GitHub) and your sanitized diff.
3. **LLM Judgment**: It sends a prompt to the LLM asking two questions:
   - Is this work aligned with the ticket?
   - Is there scope creep (unrelated changes)?
4. **Result**: The LLM returns a structured verdict which FlowCheck displays.

## 3. Usage Example

**Command**:

```bash
# Via MCP tool call in your agent
verify_intent(ticket_id="123", repo_path=".")
```

**Output**:

```json
{
  "alignment_score": 1.0,
  "is_aligned": true,
  "scope_creep_warnings": [],
  "reasoning": "The diff implements the requested 'Dark Mode' toggle in the settings page exactly as described in the ticket."
}
```

## 4. Addressing Scope Creep

If the AI Judge detects scope creep:

```json
{
  "is_aligned": false,
  "scope_creep_warnings": ["Scope Creep Detected by AI Judge"],
  "reasoning": "Ticket #123 is about 'CSS Fixes', but the diff includes a database migration for the Users table."
}
```

**Action**:

- **Split your PR**: Create a separate branch for the unrelated changes.
- **Update Ticket**: If the scope _did_ change, update the ticket description to reflect reality.

## 5. Fallback Mode

If the LLM cannot be reached (no API key, network error), FlowCheck automatically falls back to **Heuristic Mode** (v0.1 behavior).

- Uses TF-IDF cosine similarity.
- Faster but less accurate.
- You will see `reasoning: "[Fallback to TF-IDF]..."` in the output.
