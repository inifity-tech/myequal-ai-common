#!/bin/bash

# Path to the commit message file
COMMIT_MSG_FILE=$1

# Check if we should add [skip release]
if [ -f .git/COMMIT_SKIP_RELEASE ]; then
    # Read current message
    CURRENT_MSG=$(cat "$COMMIT_MSG_FILE")
    
    # Add [skip release] if not already present
    if ! echo "$CURRENT_MSG" | grep -q "\[skip release\]"; then
        echo "$CURRENT_MSG [skip release]" > "$COMMIT_MSG_FILE"
    fi
    
    # Clean up
    rm -f .git/COMMIT_SKIP_RELEASE
fi

exit 0