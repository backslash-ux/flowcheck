"""Git hook script templates for FlowCheck."""

PRE_COMMIT_HOOK = '''#!/bin/sh
# FlowCheck pre-commit hook
# Automatically checks for secrets, PII, and hygiene issues before commits
# Installed by: flowcheck install-hooks

# Allow bypass with FLOWCHECK_BYPASS=1
if [ "$FLOWCHECK_BYPASS" = "1" ]; then
    echo "⚠️  FlowCheck: Bypass enabled - skipping checks"
    # Log the bypass for audit
    flowcheck check --strict 2>/dev/null || true
    exit 0
fi

# Run FlowCheck in strict mode
echo "🔍 FlowCheck: Running pre-commit checks..."

if ! command -v flowcheck &> /dev/null; then
    echo "⚠️  FlowCheck: CLI not found in PATH"
    echo "   Install with: pip install flowcheck"
    echo "   Or run: pip install -e /path/to/flowcheck"
    exit 0  # Don't block if FlowCheck isn't installed
fi

flowcheck check --strict

exit_code=$?

if [ $exit_code -eq 2 ]; then
    echo ""
    echo "❌ FlowCheck: BLOCKED - Security issues detected!"
    echo "   Fix the issues above or bypass with: FLOWCHECK_BYPASS=1 git commit ..."
    echo ""
    exit 1
elif [ $exit_code -eq 1 ]; then
    echo ""
    echo "⚠️  FlowCheck: Warnings detected (proceeding anyway)"
    echo ""
fi

exit 0
'''


POST_COMMIT_HOOK = '''#!/bin/sh
# FlowCheck post-commit hook
# Indexes new commits for semantic search
# Installed by: flowcheck install-hooks

# Run in background to not block
(
    if command -v flowcheck &> /dev/null; then
        flowcheck index --incremental 2>/dev/null || true
    fi
) &

exit 0
'''


def get_pre_commit_hook() -> str:
    """Get the pre-commit hook script content."""
    return PRE_COMMIT_HOOK


def get_post_commit_hook() -> str:
    """Get the post-commit hook script content."""
    return POST_COMMIT_HOOK
