#!/bin/bash
# 供 www-data 通过 sudo 执行 git（WEB 在线更新检查 / 拉取）
set -euo pipefail

APP="${LIANHUAN_APP_ROOT:-/opt/lianhuan/app}"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
	if command -v sudo >/dev/null 2>&1; then
		exec sudo -n -E /bin/bash "$0" "$@"
	fi
	echo "web-git.sh: need root or passwordless sudo" >&2
	exit 1
fi

export GIT_TERMINAL_PROMPT=0
cd "$APP"
git config --global --add safe.directory "$APP" 2>/dev/null || true

auth_fetch_url() {
	local branch="${1:-main}"
	local remote_url
	remote_url="$(git config --get remote.origin.url || true)"
	if [[ -z "$remote_url" ]]; then
		echo "missing remote origin" >&2
		return 1
	fi
	if [[ -n "${GITHUB_TOKEN:-}" ]]; then
		if [[ "$remote_url" =~ ^https://github.com/(.+)$ ]]; then
			echo "https://x-access-token:${GITHUB_TOKEN}@github.com/${BASH_REMATCH[1]}"
			return 0
		fi
		if [[ "$remote_url" =~ ^https://[^/]+@github.com/(.+)$ ]]; then
			echo "https://x-access-token:${GITHUB_TOKEN}@github.com/${BASH_REMATCH[1]}"
			return 0
		fi
	fi
	echo "$remote_url"
}

if [[ "${1:-}" == "_fetch" ]]; then
	branch="${2:-main}"
	url="$(auth_fetch_url "$branch")"
	git fetch "$url" "$branch"
	exit 0
fi

exec git -C "$APP" "$@"
