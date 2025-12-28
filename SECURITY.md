# Security Policy

## Supported Versions

Use this section to tell people about which versions of your project are
currently being supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

As a security-focused tool, we take vulnerabilities very seriously.

If you discover a security issue (e.g., a bypass of the PII sanitizer, a remote code execution vector in the MCP server), please do **NOT** open a public issue.

Instead, please send an email to **security@flowcheck.dev**.

### What to include

- Description of the vulnerability.
- Steps to reproduce.
- Potential impact.

We will acknowledge your report within 48 hours.

## Indirect Prompt Injection

FlowCheck is designed to **detect** indirect prompt injection in the repositories it analyzes. However, as an LLM-connected tool, it may theoretically be susceptible to sophisticated adversarial attacks embedded in git history.

We treat "Sanitizer Bypass" (where a prompt injection payload slips past our Guardian layer) as a security vulnerability. Please report these.

## Audit Logs

FlowCheck maintains a local immutable audit log at `~/.flowcheck/audit.log`. In the event of a security incident, this log can be used for forensics.
