#!/usr/bin/env python3
"""公开仓 facefusion-releases：检查与拉取（无需 GitHub Token）。"""
from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_RELEASES_REPO = 'https://github.com/e12games/facefusion-releases.git'
DEFAULT_BRANCH = 'main'
LOG_PATH = Path(__file__).resolve().parent / 'data' / 'releases_pull.log'


def releases_repo_url() -> str:
	return os.environ.get('LIANHUAN_RELEASES_REPO', DEFAULT_RELEASES_REPO).strip() or DEFAULT_RELEASES_REPO


def releases_branch() -> str:
	return os.environ.get('LIANHUAN_RELEASES_BRANCH', DEFAULT_BRANCH).strip() or DEFAULT_BRANCH


def releases_root() -> Path:
	env = os.environ.get('LIANHUAN_RELEASES_DIR', '').strip()
	if env:
		return Path(env)
	repo_root = Path(__file__).resolve().parent.parent / 'releases'
	if repo_root.is_dir():
		return repo_root
	return Path('/opt/lianhuan/releases')


def append_log(line : str) -> None:
	LOG_PATH.parent.mkdir(parents = True, exist_ok = True)
	stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
	with LOG_PATH.open('a', encoding = 'utf-8') as handle:
		handle.write(f'{stamp} UTC {line}\n')


def git_env() -> dict[str, str]:
	env = os.environ.copy()
	env['GIT_TERMINAL_PROMPT'] = '0'
	return env


def run_git(cwd : Path, args : list[str], timeout : int = 120) -> tuple[int, str]:
	result = subprocess.run(
		['git', '-C', str(cwd), *args],
		capture_output = True,
		text = True,
		timeout = timeout,
		env = git_env()
	)
	output = (result.stdout or '') + (result.stderr or '')
	return result.returncode, output.strip()


def releases_status(fetch : bool = True) -> dict[str, Any]:
	root = releases_root()
	repo = releases_repo_url()
	branch = releases_branch()
	if not (root / '.git').is_dir():
		return {
			'ok': True,
			'deployable': True,
			'cloned': False,
			'repo': repo,
			'root': str(root),
			'branch': branch,
			'local_commit': '—',
			'remote_commit': '—',
			'update_available': True,
			'fetch_ok': True,
			'message': '尚未 clone，可点「拉取发布包」初始化。'
		}
	_, local_out = run_git(root, ['rev-parse', '--short', 'HEAD'])
	fetch_ok = True
	fetch_detail = ''
	if fetch:
		fetch_code, fetch_detail = run_git(root, ['fetch', 'origin', branch])
		fetch_ok = fetch_code == 0
	_, remote_out = run_git(root, ['rev-parse', '--short', f'origin/{branch}'])
	local = local_out.strip() or '?'
	remote = remote_out.strip() if fetch_ok else '?'
	update_available = fetch_ok and local != remote
	return {
		'ok': True,
		'deployable': True,
		'cloned': True,
		'repo': repo,
		'root': str(root),
		'branch': branch,
		'local_commit': local,
		'remote_commit': remote,
		'update_available': update_available,
		'fetch_ok': fetch_ok,
		'fetch_detail': fetch_detail
	}


def check_releases() -> dict[str, Any]:
	status = releases_status(fetch = True)
	if not status.get('fetch_ok') and status.get('cloned'):
		status['message'] = f"无法连接发布仓：{status.get('fetch_detail') or 'fetch 失败'}"
		return status
	if not status.get('cloned'):
		return status
	if status.get('update_available'):
		status['message'] = f"发布包有新版本：{status['local_commit']} → {status['remote_commit']}"
	else:
		status['message'] = f"发布包已是最新（{status['local_commit']}）"
	append_log('check: ' + status['message'])
	return status


def pull_releases() -> dict[str, Any]:
	root = releases_root()
	repo = releases_repo_url()
	branch = releases_branch()
	root.parent.mkdir(parents = True, exist_ok = True)
	if not (root / '.git').is_dir():
		append_log(f'clone {repo} -> {root}')
		result = subprocess.run(
			['git', 'clone', '--depth', '1', '-b', branch, repo, str(root)],
			capture_output = True,
			text = True,
			timeout = 180,
			env = git_env()
		)
		output = (result.stdout or '') + (result.stderr or '')
		if result.returncode != 0:
			append_log('clone failed: ' + output)
			return {'ok': False, 'reason': output or 'clone 失败'}
		msg = f'已 clone 发布包到 {root}'
		append_log(msg)
		return {'ok': True, 'message': msg}
	code, fetch_out = run_git(root, ['fetch', 'origin', branch])
	if code != 0:
		return {'ok': False, 'reason': fetch_out or 'fetch 失败'}
	code, pull_out = run_git(root, ['pull', '--ff-only', 'origin', branch])
	if code != 0:
		append_log('pull failed: ' + pull_out)
		return {'ok': False, 'reason': pull_out or 'pull 失败'}
	status = releases_status(fetch = False)
	msg = f"发布包已更新（{status.get('local_commit')}）"
	append_log(msg)
	return {'ok': True, 'message': msg}
