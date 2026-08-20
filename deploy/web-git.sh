#!/bin/bash
# 供 www-data 通过 sudo 执行 git（WEB 在线更新检查 / 拉取）
set -euo pipefail

APP="${LIANHUAN_APP_ROOT:-/opt/lianhuan/app}"
ENV_FILE="${LIANHUAN_ENV_FILE:-/etc/lianhuan.env}"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
	if command -v sudo >/dev/null 2>&1; then
		exec sudo -n -E /bin/bash "$0" "$@"
	fi
	echo "web-git.sh: need root or passwordless sudo" >&2
	exit 1
fi

# sudo -E 会保留 www-data 的 HOME，导致读不到 root 的 git 凭据；切到 root
export HOME=/root
export GIT_TERMINAL_PROMPT=0

# 加载环境变量（含 GITHUB_TOKEN）
if [[ -f "$ENV_FILE" ]]; then
	set -a
	# shellcheck disable=SC1090
	source "$ENV_FILE"
	set +a
fi

cd "$APP"
git config --global --add safe.directory "$APP" 2>/dev/null || true

auth_remote_url() {
	local remote_url path
	remote_url="$(git config --get remote.origin.url || true)"
	if [[ -z "$remote_url" ]]; then
		echo "missing remote origin" >&2
		return 1
	fi
	if [[ -n "${GITHUB_TOKEN:-}" ]]; then
		if [[ "$remote_url" =~ github.com[:/](.+)$ ]]; then
			path="${BASH_REMATCH[1]}"
			path="${path%.git}"
			echo "https://x-access-token:${GITHUB_TOKEN}@github.com/${path}.git"
			return 0
		fi
	fi
	echo "$remote_url"
}

if [[ "${1:-}" == "_fetch" ]]; then
	branch="${2:-main}"
	if [[ -n "${GITHUB_TOKEN:-}" ]]; then
		url="$(auth_remote_url)"
		git fetch "$url" "+refs/heads/${branch}:refs/remotes/origin/${branch}"
	else
		# 公开仓，或依赖 /root 下已有凭据
		if ! git fetch origin "$branch"; then
			echo "git fetch 失败。若主仓为私有，请在 /etc/lianhuan.env 设置 GITHUB_TOKEN=你的PAT 后 systemctl restart lianhuan-web" >&2
			exit 1
		fi
	fi
	exit 0
fi

if [[ "${1:-}" == "_pull" ]]; then
	branch="${2:-main}"
	# 先 fetch 再 ff-only merge，避免 “Cannot fast-forward to multiple branches”
	if [[ -n "${GITHUB_TOKEN:-}" ]]; then
		url="$(auth_remote_url)"
		git fetch "$url" "+refs/heads/${branch}:refs/remotes/origin/${branch}"
	else
		git fetch origin "$branch"
	fi
	if ! git merge --ff-only "origin/${branch}"; then
		echo "git merge --ff-only 失败。可先在 VPS 手动：cd $APP && git reset --hard origin/${branch}" >&2
		exit 1
	fi
	exit 0
fi

exec git -C "$APP" "$@"
