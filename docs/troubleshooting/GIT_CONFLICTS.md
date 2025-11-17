# Resolving Git Conflicts

## Problem: Divergent Branches

When you try to pull and see:

```
hint: You have divergent branches and need to specify how to reconcile them.
fatal: Need to specify how to reconcile divergent branches.
```

This means your local branch and the remote branch have different commits.

## Quick Fix

Choose one of these strategies:

### Option 1: Merge (Recommended)
Keep both your local changes and remote changes:

```bash
git pull --no-rebase origin claude/fix-nft-import-error-01UVkDwmNEFTCBW5f4sNwfRE
```

This creates a merge commit combining both histories.

### Option 2: Rebase
Replay your local commits on top of remote changes:

```bash
git pull --rebase origin claude/fix-nft-import-error-01UVkDwmNEFTCBW5f4sNwfRE
```

This creates a linear history but rewrites your commits.

### Option 3: Overwrite Local Changes
Discard your local changes and use remote version:

```bash
git fetch origin claude/fix-nft-import-error-01UVkDwmNEFTCBW5f4sNwfRE
git reset --hard origin/claude/fix-nft-import-error-01UVkDwmNEFTCBW5f4sNwfRE
```

⚠️ **WARNING**: This permanently deletes your local changes!

## Understanding the Issue

### Why This Happens

1. You made commits locally
2. Someone (or a CI system) pushed commits to the remote branch
3. Git doesn't know whether to:
   - Keep your changes
   - Keep remote changes
   - Combine both

### Branch States

```
# Your local branch
A - B - C - D (your commit)

# Remote branch
A - B - C - E (remote commit)
```

Both branched from C, creating divergent histories.

## Step-by-Step Resolution

### 1. Check Current Status

```bash
git status
git log --oneline -5
```

### 2. View Remote Changes

```bash
git fetch origin claude/fix-nft-import-error-01UVkDwmNEFTCBW5f4sNwfRE
git log origin/claude/fix-nft-import-error-01UVkDwmNEFTCBW5f4sNwfRE --oneline -5
```

### 3. Compare Changes

```bash
# See what's different
git diff HEAD origin/claude/fix-nft-import-error-01UVkDwmNEFTCBW5f4sNwfRE
```

### 4. Choose Resolution Strategy

Based on what you see:

**If remote changes look good**: Use Option 3 (overwrite)
```bash
git reset --hard origin/claude/fix-nft-import-error-01UVkDwmNEFTCBW5f4sNwfRE
```

**If you want both changes**: Use Option 1 (merge)
```bash
git pull --no-rebase origin claude/fix-nft-import-error-01UVkDwmNEFTCBW5f4sNwfRE
```

**If you want clean history**: Use Option 2 (rebase)
```bash
git pull --rebase origin claude/fix-nft-import-error-01UVkDwmNEFTCBW5f4sNwfRE
```

## Set Default Behavior

To avoid this prompt in the future:

```bash
# For merge strategy (recommended)
git config pull.rebase false

# For rebase strategy
git config pull.rebase true

# For fast-forward only (safest, will error if diverged)
git config pull.ff only
```

## Common Scenarios

### Scenario 1: You Have No Important Local Changes

```bash
# Just use the remote version
git fetch origin
git reset --hard origin/claude/fix-nft-import-error-01UVkDwmNEFTCBW5f4sNwfRE
```

### Scenario 2: You Made Local Changes You Want to Keep

```bash
# Stash your changes temporarily
git stash

# Pull remote changes
git pull origin claude/fix-nft-import-error-01UVkDwmNEFTCBW5f4sNwfRE

# Apply your changes back
git stash pop
```

### Scenario 3: You Want Both Sets of Changes

```bash
# Merge both histories
git pull --no-rebase origin claude/fix-nft-import-error-01UVkDwmNEFTCBW5f4sNwfRE

# Resolve any conflicts if they occur
# Edit conflicted files
git add .
git commit -m "Merge remote changes"
```

## Handling Merge Conflicts

If you get merge conflicts:

### 1. See Conflicted Files

```bash
git status
```

Look for files marked as "both modified".

### 2. Open and Edit Conflicts

Conflicts look like:

```
<<<<<<< HEAD
Your local changes
=======
Remote changes
>>>>>>> origin/branch
```

Edit the file to keep what you want, removing the conflict markers.

### 3. Mark as Resolved

```bash
git add filename
```

### 4. Complete the Merge

```bash
git commit
```

Or if rebasing:

```bash
git rebase --continue
```

## Preventing Future Conflicts

### Before Making Changes

```bash
# Always pull before starting work
git pull origin branch-name
```

### Use Separate Branches

```bash
# Create your own branch
git checkout -b my-feature-branch

# Make changes
git add .
git commit -m "My changes"

# Merge remote changes when ready
git fetch origin
git merge origin/claude/fix-nft-import-error-01UVkDwmNEFTCBW5f4sNwfRE
```

### Communicate with Team

If working with others:
- Coordinate who's working on what
- Pull frequently
- Push often
- Use feature branches

## Emergency: Start Over

If everything is broken:

```bash
# Backup your current work (optional)
git stash

# Get clean copy of remote branch
git fetch origin
git checkout claude/fix-nft-import-error-01UVkDwmNEFTCBW5f4sNwfRE
git reset --hard origin/claude/fix-nft-import-error-01UVkDwmNEFTCBW5f4sNwfRE

# If you want your stashed changes back
git stash pop
```

## Getting Help

```bash
# View git help on pulling
git help pull

# View git help on merging
git help merge

# View git help on rebasing
git help rebase
```

## Summary

For most users, the safest approach:

```bash
# Set merge as default
git config pull.rebase false

# Pull with merge
git pull origin branch-name
```

This keeps both histories and is the most forgiving approach.
