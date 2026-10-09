#!/usr/bin/env bash
# Rebuild the X Digest site and push it to github.com/theodoruszq/x-digest (served from /docs on main).
#   ./publish.sh ["commit message"]
# Env: X_DIGEST_SRC   folder with YYYY-MM-DD.md day files (default /workspace/x-digest; skipped if missing)
#      GITHUB_TOKEN_FILE  token file (default ~/.secrets/github_xdigest_token); never written to git config.
set -euo pipefail
cd "$(dirname "$0")"
SRC="${X_DIGEST_SRC:-/workspace/x-digest}"
TOKEN_FILE="${GITHUB_TOKEN_FILE:-$HOME/.secrets/github_xdigest_token}"
REMOTE="https://github.com/theodoruszq/x-digest.git"

if [ -d "$SRC" ]; then
  find "$SRC" -maxdepth 1 -regextype posix-extended -regex '.*/[0-9]{4}-[0-9]{2}-[0-9]{2}\.md' -exec cp {} content/ \;
fi
python3 build.py

git add -A
if git diff --cached --quiet; then
  echo "nothing to publish"; exit 0
fi
git -c user.name="${GIT_AUTHOR_NAME:-X Digest Bot}" -c user.email="${GIT_AUTHOR_EMAIL:-theodoruszq@users.noreply.github.com}" \
  commit -q -m "${1:-Update digest $(date +%F\ %H:%M)}"
# One-off credential helper: reads the token from the file at push time only.
git -c credential.helper= \
    -c "credential.helper=!f() { echo username=x-access-token; echo \"password=\$(cat '$TOKEN_FILE')\"; }; f" \
    push "$REMOTE" HEAD:main
echo "pushed; Pages will redeploy https://theodoruszq.github.io/x-digest/ in ~1 min"
