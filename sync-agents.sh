#!/bin/bash
#
# Sync this repo's AGENTS.md to allowed RTD sibling repos that already have one,
# then commit and push to main.
#
# Usage:
#   ./sync-agents.sh             # dry run - show what would change
#   ./sync-agents.sh --apply     # actually copy, commit, and push

set -euo pipefail

APPLY=0
if [ "${1:-}" = "--apply" ]; then
    APPLY=1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$SCRIPT_DIR/AGENTS.md"
if [ -n "${RTDDEV_TMP_PATH:-}" ] && [ -d "$RTDDEV_TMP_PATH" ]; then
    TARGET_ROOT="$RTDDEV_TMP_PATH"
else
    TARGET_ROOT="$(dirname "$SCRIPT_DIR")"
fi
TARGET_REPOS=(
    readthedocs.org
    readthedocs-ext
    ext-theme
    readthedocs-ops
    readthedocs-corporate
    readthedocs-corporate-ops
)

if [ ! -f "$SOURCE" ]; then
    echo "❌ Source not found: $SOURCE"
    exit 1
fi

COMMIT_MSG="Sync AGENTS.md from readthedocs/common"

echo "Source: $SOURCE"
echo "Target: $TARGET_ROOT"
echo "Mode:   $([ $APPLY -eq 1 ] && echo APPLY || echo 'dry run (use --apply to push)')"
echo

for name in "${TARGET_REPOS[@]}"; do
    repo="$TARGET_ROOT/$name"
    target_md="$repo/AGENTS.md"

    # Must be a git repo
    if [ ! -d "$repo/.git" ]; then
        echo "⏭  $name: not a git repo, skipping"
        continue
    fi

    if [ ! -f "$target_md" ]; then
        echo "⏭  $name: AGENTS.md not found, skipping"
        continue
    fi

    echo "📦 $name"

    # Working tree must be clean (ignoring untracked) so we don't sweep up unrelated changes
    if ! git -C "$repo" diff --quiet || ! git -C "$repo" diff --cached --quiet; then
        echo "   ⚠️  uncommitted changes, skipping"
        continue
    fi

    # Must be on main; switch there first if the checkout is clean.
    branch="$(git -C "$repo" rev-parse --abbrev-ref HEAD)"
    if [ "$branch" != "main" ]; then
        if [ $APPLY -eq 0 ]; then
            echo "   would checkout main from '$branch'"
        elif git -C "$repo" checkout main; then
            echo "   checked out main from '$branch'"
        else
            echo "   ⚠️  could not checkout main from '$branch', skipping"
            continue
        fi
    fi

    # Identical? nothing to do
    if cmp -s "$SOURCE" "$target_md"; then
        echo "   ✓ already up to date"
        continue
    fi

    if [ $APPLY -eq 0 ]; then
        echo "   would update (diff vs source):"
        diff -u "$target_md" "$SOURCE" | sed 's/^/     /' | head -40 || true
        continue
    fi

    # Pull latest main first
    if ! git -C "$repo" pull --ff-only origin main; then
        echo "   ❌ pull failed, skipping"
        continue
    fi

    cp "$SOURCE" "$target_md"

    if git -C "$repo" diff --quiet -- AGENTS.md; then
        echo "   ✓ no change after pull"
        continue
    fi

    git -C "$repo" add AGENTS.md
    git -C "$repo" commit -m "$COMMIT_MSG"
    git -C "$repo" push origin main
    echo "   ✅ pushed"
done

echo
echo "Done."
