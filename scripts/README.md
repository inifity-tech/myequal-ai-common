# Git Hooks and Auto-Versioning

This repository uses automated versioning and release management for code changes.

## Setup

Run the setup script to install git hooks:

```bash
./scripts/setup-hooks.sh
```

## How It Works

### Automatic Version Bumping

When you push code changes to the `master` branch:

1. **Code Changes Detection**: The workflow detects if any Python files or `pyproject.toml` were changed
2. **Version Bump**: 
   - Default: Patch version (0.1.1 → 0.1.2)
   - `feat:` prefix: Minor version (0.1.1 → 0.2.0)
   - `BREAKING:` prefix: Major version (0.1.1 → 1.0.0)
3. **Auto Release**: Creates a git tag and triggers the publish workflow

### Pre-commit Hook

When committing code changes to master, you'll be prompted:

```
🔍 Code changes detected in:
src/myequal_ai_common/utils/sample.py

📦 Would you like to create a new release for these changes?
   (This will auto-increment the version after push)

Options:
  1) Yes, create a patch release (default)
  2) Yes, create a minor release (new feature)
  3) Yes, create a major release (breaking change)
  4) No, skip release

Your choice [1-4, default=1]: 
```

### Skipping Releases

To skip automatic release creation:
- Choose option 4 in the pre-commit hook
- Or manually add `[skip release]` to your commit message
- The workflow will detect this and skip version bumping

### Examples

```bash
# Patch release (0.1.1 → 0.1.2)
git commit -m "fix: correct typo in function"

# Minor release (0.1.1 → 0.2.0)
git commit -m "feat: add new utility functions"

# Major release (0.1.1 → 1.0.0)
git commit -m "BREAKING: change API signatures"

# No release
git commit -m "docs: update README [skip release]"
```

## File Patterns

Only changes to these files trigger version bumps:
- `*.py` - Python source files
- `pyproject.toml` - Package configuration

Changes to documentation, CI/CD files, etc. do not trigger releases.