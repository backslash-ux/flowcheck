# Managing Security Flags

One of FlowCheck's primary jobs is to stop you from accidentally committing secrets or PII. When `get_flow_state` returns entries in `security_flags`, you must take action.

## 1. Understanding the Flags

You might see flags like:

- `⚠️ SECRETS: Potential secrets detected in diff`
- `⚠️ PII: Personal information detected in diff`
- `⚠️ INJECTION: Prompt injection pattern detected`

This means the **Guardian Layer** has scanned your uncommitted changes and found patterns that look dangerous.

## 2. Immediate Action: DO NOT PUSH

**Stop**. Do not run `git commit` or `git push`.
If you are using an AI agent, instruct it to **stop and review**.

## 3. Reviewing the Issue

1. **Check your diff**:
   ```bash
   git diff
   ```
2. **Look for**:
   - API Keys (`sk-...`, `AWS_ACCESS_KEY...`)
   - Hardcoded passwords
   - Personal emails or phone numbers in code comments or test data
   - Strange prompt-like strings ("Ignore previous instructions")

## 4. Remediation

### Scenario A: It is a real secret

**Fix**: Remove the secret from the code. Use environment variables instead.

1. Add the value to `.env`.
2. Update code to use `os.environ.get("MY_SECRET")`.
3. Save file.
4. Run `get_flow_state` again to verify the flag is gone.

### Scenario B: It is a false positive

**Fix**: If FlowCheck is flagging a random string as a secret, you can:

1. **Sanitize it**: If you just need to share the code with an agent, use the `sanitize_content` tool to create a clean version.
2. **Ignore it (Advanced)**: Currently, FlowCheck is strict. In v0.2, you cannot "allowlist" a specific secret pattern easily without code changes. The safest path is to refactor the code to avoid the pattern.

## 5. Pre-Sharing Hygiene (The `sanitize_content` Tool)

Before you strip-paste code into ChatGPT or another web LLM, use FlowCheck to clean it:

**Input**:

> "Here is my config file with my database password..."

**Agent Action**:

> Calls `sanitize_content(content=...)`

**Result**:

```python
db_password = "[REDACTED_SECRET_1]"
```

Use this output for your chat session. It is safe to share.
