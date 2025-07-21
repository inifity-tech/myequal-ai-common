#!/bin/bash

echo "🔧 Setting up git hooks..."

# Create hooks directory if it doesn't exist
mkdir -p .git/hooks

# Install pre-commit hook
if [ -f scripts/pre-commit-release-check.sh ]; then
    cp scripts/pre-commit-release-check.sh .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit
    echo "✅ Pre-commit hook installed"
else
    echo "❌ Pre-commit script not found"
fi

# Install commit-msg hook
if [ -f scripts/commit-msg-hook.sh ]; then
    cp scripts/commit-msg-hook.sh .git/hooks/commit-msg
    chmod +x .git/hooks/commit-msg
    echo "✅ Commit-msg hook installed"
else
    echo "❌ Commit-msg script not found"
fi

echo ""
echo "🎉 Git hooks setup complete!"
echo ""
echo "📝 How it works:"
echo "   - When committing code changes to master, you'll be asked about creating a release"
echo "   - Use 'feat:' prefix for minor version bumps"
echo "   - Use 'BREAKING:' prefix for major version bumps"
echo "   - Add '[skip release]' to commit message to skip auto-release"
echo ""