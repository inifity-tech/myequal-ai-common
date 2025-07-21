#!/bin/bash

# Check if we're on master branch
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" != "master" ]; then
    exit 0
fi

# Check for code changes
CODE_PATTERNS="\.py$|pyproject\.toml$"
STAGED_FILES=$(git diff --cached --name-only)

if echo "$STAGED_FILES" | grep -E "$CODE_PATTERNS" > /dev/null; then
    echo "🔍 Code changes detected in:"
    echo "$STAGED_FILES" | grep -E "$CODE_PATTERNS"
    echo ""
    
    # Ask user about release
    echo "📦 Would you like to create a new release for these changes?"
    echo "   (This will auto-increment the version after push)"
    echo ""
    echo "Options:"
    echo "  1) Yes, create a patch release (default)"
    echo "  2) Yes, create a minor release (new feature)"
    echo "  3) Yes, create a major release (breaking change)"
    echo "  4) No, skip release"
    echo ""
    read -p "Your choice [1-4, default=1]: " choice
    
    case $choice in
        2)
            echo ""
            echo "💡 Tip: Start your commit message with 'feat:' for automatic minor version bump"
            echo "Example: feat: add new utility functions"
            ;;
        3)
            echo ""
            echo "💡 Tip: Start your commit message with 'BREAKING:' for automatic major version bump"
            echo "Example: BREAKING: change API signatures"
            ;;
        4)
            echo ""
            echo "💡 Adding '[skip release]' to your commit message to prevent auto-release"
            echo ""
            read -p "Would you like me to add '[skip release]' to your commit message? [y/N]: " add_skip
            if [[ $add_skip =~ ^[Yy]$ ]]; then
                # This will be picked up by the commit-msg hook
                echo "SKIP_RELEASE=1" > .git/COMMIT_SKIP_RELEASE
            fi
            ;;
        *)
            echo ""
            echo "✅ Will create a patch release after push"
            ;;
    esac
else
    echo "📝 Only non-code files changed. No version bump needed."
fi

exit 0