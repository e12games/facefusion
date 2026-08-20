#!/usr/bin/env python3
"""公开仓 facefusion-releases：HTTP 检查 + 可选本地 git 缓存。"""
from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from update_service import (
	fetch_remote_manifest,
	load_manifest_local,
	releases_dir,
	releases_raw_base,
	releases_repo_url
)

DEFAULT_BRANCH = 'main'
LOG_PATH = Path(__file__).resolve().parent / 'data' / 'releases_pull.log'
FETCH_UA = 'Mozilla/5.0 (compatible; LianHuan/1)'


def releases_branch() -> str:
	return os.environ.get('LIANHUAN_RELEASES_BRANCH', DEFAULT_BRANCH).strip() or DEFAULT_BRANCH


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


def remote_manifest_ok() -> tuple[bool, str, Optional[dict[str, Any]]]:
	manifest = fetch_remote_manifest()
	if manifest is None:
		return False, '无法读取公开仓 manifest.json', None
	version = str(manifest.get('version') or '')
	files = len(manifest.get('files') or [])
	return True, f'公开仓 manifest 版本 {version} · {files} 个文件', manifest


def releases_status(fetch : bool = True) -> dict[str, Any]:
	root = releases_dir()
	repo = releases_repo_url()
	raw = releases_raw_base()
	ok, detail, manifest = remote_manifest_ok()
	remote_version = str(manifest.get('version') or '—') if manifest else '—'
	local_manifest = load_manifest_local()
	local_version = str(local_manifest.get('version') or '—')
	cloned = (root / '.git').is_dir()
	local_commit = '—'
	if cloned:
		_, local_out = run_git(root, ['rev-parse', '--short', 'HEAD'])
		local_commit = local_out.strip() or '—'
	return {
		'ok': True,
		'deployable': True,
		'cloned': cloned,
		'repo': repo,
		'raw_base': raw,
		'root': str(root),
		'branch': releases_branch(),
		'remote_version': remote_version,
		'local_version': local_version,
		'local_commit': local_commit,
		'update_available': ok and remote_version not in ('—', local_version),
		'fetch_ok': ok,
		'fetch_detail': detail if ok else detail,
		'remote_manifest_ok': ok
	}


def check_releases() -> dict[str, Any]:
	status = releases_status(fetch = True)
	if not status.get('remote_manifest_ok'):
		status['message'] = status.get('fetch_detail') or '无法连接公开仓'
		return status
	if status.get('update_available'):
		status['message'] = (
			f"公开仓有新版本：本地 {status['local_version']} → 远程 {status['remote_version']}"
		)
	else:
		status['message'] = (
			f"公开仓已就绪（{status['remote_version']}）· 源 {status['raw_base']}"
		)
	append_log('check: ' + status['message'])
	return status


def pull_releases() -> dict[str, Any]:
	root = releases_dir()
	repo = releases_repo_url()
	branch = releases_branch()
	root.parent.mkdir(parents = True, exist_ok = True)
	ok, detail, manifest = remote_manifest_ok()
	if not ok:
		return {'ok': False, 'reason': detail}
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
		msg = f'已 clone 到 {root}（客户端已可直接从 GitHub 拉取，本地缓存可选）'
		append_log(msg)
		return {'ok': True, 'message': msg}
	code, fetch_out = run_git(root, ['fetch', 'origin', branch])
	if code != 0:
		return {'ok': False, 'reason': fetch_out or 'fetch 失败'}
	code, pull_out = run_git(root, ['pull', '--ff-only', 'origin', branch])
	if code != 0:
		append_log('pull failed: ' + pull_out)
		return {'ok': False, 'reason': pull_out or 'pull 失败'}
	version = str(manifest.get('version') or '') if manifest else ''
	msg = f'本地缓存已更新（{version}）'
	append_log(msg)
	return {'ok': True, 'message': msg}
