#!/usr/bin/env bash
# Rebuild the X Digest site and push it to github.com/theodoruszq/x-digest (Pages serves main:/docs).
#   ./publish.sh ["commit message"]
# Env: X_DIGEST_SRC       folder with YYYY-MM-DD.md day files (default /workspace/x-digest; skipped if missing)
#      GITHUB_TOKEN_FILE  token file (default ~/.secrets/github_xdigest_token). The token is only used in a
#                         one-off push URL, masked in output, and never written to git config.
set -euo pipefail
cd "$(dirname "$0")"
SRC="${X_DIGEST_SRC:-/workspace/x-digest}"
TOKEN_FILE="${GITHUB_TOKEN_FILE:-$HOME/.secrets/github_xdigest_token}"
REPO="github.com/theodoruszq/x-digest.git"

if [ -d "$SRC" ]; then
  find "$SRC" -maxdepth 1 -regextype posix-extended -regex '.*/[0-9]{4}-[0-9]{2}-[0-9]{2}\.md' -exec cp {} content/ \;
fi
python3 build.py

git add -A
if ! git diff --cached --quiet; then
  git -c user.name="${GIT_AUTHOR_NAME:-X Digest Bot}" -c user.email="${GIT_AUTHOR_EMAIL:-theodoruszq@users.noreply.github.com}" \
    commit -q -m "${1:-Update digest $(date +%F\ %H:%M)}"
  echo "committed $(git rev-parse --short HEAD)"
fi

# Push whenever local main differs from the remote (covers earlier unpushed commits too).
LOCAL="$(git rev-parse HEAD)"
REMOTE_SHA="$(git ls-remote "https://$REPO" refs/heads/main | cut -f1 || true)"
if [ "$LOCAL" = "$REMOTE_SHA" ]; then
  echo "remote main already at $(git rev-parse --short HEAD); nothing to publish"; exit 0
fi
T="$(cat "$TOKEN_FILE")"
set +e
git push "https://x-access-token:${T}@${REPO}" HEAD:main 2>&1 | sed "s/${T}/***/g"
status=${PIPESTATUS[0]}
set -e
unset T
[ "$status" -eq 0 ] || { echo "push failed ($status)"; exit "$status"; }
echo "pushed $(git rev-parse --short HEAD); Pages redeploys https://theodoruszq.github.io/x-digest/ in ~1 min"
