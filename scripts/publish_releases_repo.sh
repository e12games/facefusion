#!/bin/bash
# 将 releases/ 推送到公开仓 facefusion-releases
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/releases"
REPO="${1:-https://github.com/e12games/facefusion-releases.git}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

[[ -d "$SRC/files" ]] || { echo "缺少 $SRC/files"; exit 1; }

if [[ -d "$SRC/.git" ]]; then
	cd "$SRC"
	git add -A
	git diff --cached --quiet && { echo "无变更"; exit 0; }
	git commit -m "release $(grep -o '"version": "[^"]*"' manifest.json | head -1 || echo update)"
	git push origin HEAD
	echo "已从 $SRC 直接 push"
	exit 0
fi

git clone "$REPO" "$WORK/repo"
rsync -a --delete --exclude '.git' "$SRC/" "$WORK/repo/"
cd "$WORK/repo"
git add -A
git diff --cached --quiet && { echo "无变更"; exit 0; }
git commit -m "release $(grep -o '"version": "[^"]*"' manifest.json | head -1 || echo update)"
git push origin HEAD
echo "已推送到 $REPO"
