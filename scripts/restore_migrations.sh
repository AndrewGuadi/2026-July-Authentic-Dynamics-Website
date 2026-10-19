#!/usr/bin/env bash
# Discard local migration changes and extras; use the checked-out commit's history.
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
git ls-files --error-unmatch migrations/env.py >/dev/null
git restore --source=HEAD --worktree -- migrations/
git clean -fdx -- migrations/
echo "Migration files now match the checked-out commit."
