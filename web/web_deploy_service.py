#!/usr/bin/env python3
"""VPS 上 WEB 自身：git 检查与一键更新。"""
from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WEB_ROOT = Path(__file__).resolve().parent
APP_ROOT = Path(os.environ.get('LIANHUAN_APP_ROOT', str(WEB_ROOT.parent)))
LOG_PATH = WEB_ROOT / 'data' / 'web_update.log'
LOCK_PATH = WEB_ROOT / 'data' / 'web_update.lock'
UPDATE_SCRIPT = APP_ROOT / 'deploy' / 'web-self-update.sh'
BRANCH = os.environ.get('LIANHUAN_BRANCH', 'main')


def append_log(line : str) -> None:
	LOG_PATH.parent.mkdir(parents = True, exist_ok = True)
	stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
	with LOG_PATH.open('a', encoding = 'utf-8') as handle:
		handle.write(f'{stamp} UTC {line}\n')


def read_log_tail(max_lines : int = 24) -> str:
	if not LOG_PATH.is_file():
		return ''
	lines = LOG_PATH.read_text(encoding = 'utf-8', errors = 'ignore').splitlines()
	return '\n'.join(lines[-max_lines:])


def is_deploy_environment() -> bool:
	return (APP_ROOT / '.git').is_dir()


def run_git(args : list[str], timeout : int = 120) -> tuple[int, str]:
	result = subprocess.run(
		['git', '-C', str(APP_ROOT), *args],
		capture_output = True,
		text = True,
		timeout = timeout
	)
	output = (result.stdout or '') + (result.stderr or '')
	return result.returncode, output.strip()


def git_status(fetch : bool = True) -> dict[str, Any]:
	if not is_deploy_environment():
		return {
			'ok': False,
			'deployable': False,
			'reason': '当前环境不是 Git 部署目录（本地开发不可用，仅 VPS 生产环境可用）。',
			'app_root': str(APP_ROOT)
		}
	_, branch_out = run_git(['rev-parse', '--abbrev-ref', 'HEAD'])
	_, local_out = run_git(['rev-parse', '--short', 'HEAD'])
	fetch_ok = True
	fetch_detail = ''
	if fetch:
		fetch_code, fetch_detail = run_git(['fetch', 'origin', BRANCH])
		fetch_ok = fetch_code == 0
	_, remote_out = run_git(['rev-parse', '--short', f'origin/{BRANCH}'])
	local = local_out.strip() or '?'
	remote = remote_out.strip() or '?'
	branch = branch_out.strip() or BRANCH
	update_available = fetch_ok and local != '?' and remote != '?' and local != remote
	return {
		'ok': True,
		'deployable': True,
		'app_root': str(APP_ROOT),
		'branch': branch,
		'local_commit': local,
		'remote_commit': remote,
		'update_available': update_available,
		'fetch_ok': fetch_ok,
		'fetch_detail': fetch_detail,
		'locked': LOCK_PATH.is_file()
	}


def check_web_update() -> dict[str, Any]:
	status = git_status(fetch = True)
	if not status.get('ok'):
		return status
	if not status.get('fetch_ok'):
		status['message'] = f"无法连接 Git 远程：{status.get('fetch_detail') or 'fetch 失败'}"
		return status
	if status.get('update_available'):
		status['message'] = (
			f"发现 WEB 新版本：{status['local_commit']} → {status['remote_commit']}（{status['branch']}）"
		)
	else:
		status['message'] = f"WEB 已是最新（{status['local_commit']}）"
	append_log('check: ' + status['message'])
	return status


def apply_web_update() -> dict[str, Any]:
	if not is_deploy_environment():
		return {'ok': False, 'reason': '当前环境不是 Git 部署目录。'}
	if LOCK_PATH.is_file():
		return {'ok': False, 'reason': '更新正在进行中，请稍后再试。'}
	if not UPDATE_SCRIPT.is_file():
		return {'ok': False, 'reason': f'未找到更新脚本：{UPDATE_SCRIPT}'}
	status = git_status(fetch = True)
	if not status.get('fetch_ok'):
		return {'ok': False, 'reason': status.get('fetch_detail') or 'git fetch 失败'}
	try:
		LOCK_PATH.write_text('1', encoding = 'utf-8')
		append_log('apply: start web-self-update.sh')
		subprocess.Popen(
			['/bin/bash', str(UPDATE_SCRIPT)],
			cwd = str(APP_ROOT),
			stdout = subprocess.DEVNULL,
			stderr = subprocess.DEVNULL,
			start_new_session = True
		)
		msg = '已开始从 GitHub 拉取并重启 WEB 服务，约 10–30 秒中断。请稍后刷新本页。'
		if status.get('update_available'):
			msg = (
				f"更新 {status['local_commit']} → {status['remote_commit']}。"
				+ msg
			)
		append_log('apply: ' + msg)
		return {'ok': True, 'message': msg}
	except Exception as error:
		LOCK_PATH.unlink(missing_ok = True)
		append_log(f'apply failed: {error}')
		return {'ok': False, 'reason': str(error)}
