#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""启动前检查更新：增量下载 internal/app 文件，失败可回滚。"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from lianhuan_client import (
	api_base,
	app_dir,
	fetch_json,
	http_request,
	is_allowed_update_path,
	package_root,
	read_local_version,
	resolve_update_target,
	update_dir,
	version_gt
)

# 公开仓默认下载根（与 LIANHUAN_RELEASES_RAW_BASE 一致）
RELEASES_RAW_BASE = 'https://raw.githubusercontent.com/e12games/facefusion-releases/main'


def sha256_file(path : Path) -> str:
	digest = hashlib.sha256()
	with path.open('rb') as handle:
		for chunk in iter(lambda: handle.read(1024 * 1024), b''):
			digest.update(chunk)
	return digest.hexdigest()


def load_state(state_path : Path) -> dict:
	if state_path.is_file():
		try:
			return json.loads(state_path.read_text(encoding = 'utf-8'))
		except Exception:
			pass
	return {}


def save_state(state_path : Path, version : str) -> None:
	state_path.parent.mkdir(parents = True, exist_ok = True)
	payload = {'version': version}
	state_path.write_text(json.dumps(payload, ensure_ascii = False, indent = 2), encoding = 'utf-8')


def read_current_version(app_path : Path, state_path : Path) -> str:
	current = read_local_version(app_path)
	if load_state(state_path).get('version'):
		current = str(load_state(state_path).get('version'))
	return current


def ask_update(latest : str, notes : str) -> bool:
	try:
		import tkinter as tk
		from tkinter import messagebox
		root = tk.Tk()
		root.withdraw()
		message = f'发现新版本 {latest}。'
		if notes.strip():
			message += f'\n\n{notes.strip()}'
		message += '\n\n是否现在更新？（不强制，选「否」可继续）'
		answer = messagebox.askyesno('脸幻 · 更新', message)
		root.destroy()
		return answer
	except Exception:
		return False


def show_info(message : str) -> None:
	try:
		import tkinter as tk
		from tkinter import messagebox
		root = tk.Tk()
		root.withdraw()
		messagebox.showinfo('脸幻 · 更新', message)
		root.destroy()
	except Exception:
		print(message)


def show_error(message : str) -> None:
	try:
		import tkinter as tk
		from tkinter import messagebox
		root = tk.Tk()
		root.withdraw()
		messagebox.showerror('脸幻 · 更新', message)
		root.destroy()
	except Exception:
		print(message, file = sys.stderr)


def download_file(url : str, dest : Path) -> None:
	dest.parent.mkdir(parents = True, exist_ok = True)
	with http_request(url) as response, dest.open('wb') as handle:
		shutil.copyfileobj(response, handle)


def backup_file(source : Path, backup_root : Path, relative : str) -> None:
	if source.is_file():
		target = backup_root / relative.replace('/', '\\')
		target.parent.mkdir(parents = True, exist_ok = True)
		shutil.copy2(source, target)


def apply_manifest(manifest : dict, app_path : Path, work_dir : Path) -> None:
	files = manifest.get('files') or []
	version = str(manifest.get('version') or '').strip()
	if not version or not files:
		raise RuntimeError('没有可更新的文件。')
	backup_root = work_dir / 'backup' / version
	staging_root = work_dir / 'staging' / version
	pending_root = work_dir / 'pending' / version

	for folder in (backup_root, staging_root, pending_root):
		if folder.exists():
			shutil.rmtree(folder)
		folder.mkdir(parents = True, exist_ok = True)

	backed_up : list[tuple[Path, str]] = []
	try:
		for item in files:
			relative = str(item.get('path') or '')
			if not is_allowed_update_path(relative):
				raise RuntimeError(f'不允许更新的路径：{relative}')
			target = resolve_update_target(app_path, relative)
			if target is None:
				raise RuntimeError(f'不允许更新的路径：{relative}')
			relative = relative.replace('\\', '/').lstrip('/')
			expected_hash = str(item.get('sha256') or '').lower()
			expected_size = int(item.get('size') or 0)
			url = str(item.get('url') or '').strip()
			if not url:
				url = f'{RELEASES_RAW_BASE}/files/{relative}'
			pending = pending_root / relative.replace('/', '\\')
			download_file(url, pending)
			actual_hash = sha256_file(pending)
			actual_size = pending.stat().st_size
			if expected_hash and actual_hash != expected_hash:
				raise RuntimeError(f'校验失败：{relative}')
			if expected_size and actual_size != expected_size:
				raise RuntimeError(f'大小不符：{relative}')
			staged = staging_root / relative.replace('/', '\\')
			staged.parent.mkdir(parents = True, exist_ok = True)
			shutil.copy2(pending, staged)

		for item in files:
			relative = str(item.get('path') or '').replace('\\', '/').lstrip('/')
			target = resolve_update_target(app_path, relative)
			if target is None:
				raise RuntimeError(f'不允许更新的路径：{relative}')
			staged = staging_root / relative.replace('/', '\\')
			backup_file(target, backup_root, relative)
			target.parent.mkdir(parents = True, exist_ok = True)
			shutil.copy2(staged, target)
			backed_up.append((target, relative))
	except Exception:
		for target, relative in backed_up:
			backup = backup_root / relative.replace('/', '\\')
			if backup.is_file():
				target.parent.mkdir(parents = True, exist_ok = True)
				shutil.copy2(backup, target)
		raise
	finally:
		shutil.rmtree(pending_root, ignore_errors = True)
		shutil.rmtree(staging_root, ignore_errors = True)


def check_update_status() -> dict[str, Any]:
	root = package_root()
	app_path = app_dir(root)
	state_path = update_dir(root) / 'state.json'
	current = read_current_version(app_path, state_path)
	code, version_info = fetch_json('/api/version')
	status : dict[str, Any] = {
		'ok': code == 200 and version_info.get('ok', True),
		'current': current,
		'latest': '',
		'notes': '',
		'update_enabled': bool(version_info.get('update_enabled', True)),
		'update_on_startup': bool(version_info.get('update_on_startup', True)),
		'available': False,
		'files_count': 0,
		'manifest': {}
	}
	if not status['ok']:
		status['reason'] = '连不上更新服务器。'
		return status
	if not status['update_enabled']:
		status['reason'] = '管理员已关闭客户端在线更新。'
		return status
	latest = str(version_info.get('version') or version_info.get('recommended_version') or '').strip()
	notes = str(version_info.get('notes') or '')
	status['latest'] = latest
	status['notes'] = notes
	if not latest or not version_gt(latest, current):
		return status
	code, manifest = fetch_json(f'/api/update/manifest?current={current}')
	if code != 200:
		status['reason'] = '无法获取更新清单。'
		return status
	files = manifest.get('files') or []
	status['manifest'] = manifest
	status['files_count'] = len(files)
	status['available'] = bool(files)
	if not files:
		status['reason'] = '服务器暂无增量文件。'
	return status


def run_update_flow(*, interactive : bool = True, manual : bool = False) -> int:
	root = package_root()
	app_path = app_dir(root)
	work_dir = update_dir(root)
	work_dir.mkdir(parents = True, exist_ok = True)
	state_path = work_dir / 'state.json'

	status = check_update_status()
	if not status.get('ok'):
		if manual or interactive:
			show_error(str(status.get('reason') or '检查更新失败。'))
		return 1 if manual else 0
	if not status.get('update_enabled'):
		if manual:
			show_info('管理员已关闭在线更新。')
		return 0
	if not status.get('available'):
		if manual:
			show_info(f"已是最新版本（{status.get('current')}）。")
		return 0
	latest = str(status.get('latest') or '')
	notes = str(status.get('notes') or '')
	manifest = status.get('manifest') or {}
	if interactive and not ask_update(latest, notes or str(manifest.get('notes') or '')):
		return 0
	try:
		apply_manifest(manifest, app_path, work_dir)
		save_state(state_path, latest)
		version_file = app_path / 'lianhuan_version.txt'
		version_file.write_text(latest + '\n', encoding = 'utf-8')
	except Exception as error:
		show_error(f'更新失败，已尝试恢复。\n{error}')
		return 1
	if manual:
		show_info(f'更新完成，当前版本 {latest}。')
	return 0


def main() -> int:
	manual = '--manual' in sys.argv
	if '--check-only' in sys.argv:
		status = check_update_status()
		print(json.dumps(status, ensure_ascii = False))
		return 0 if status.get('ok') else 1
	if not manual:
		code, version_info = fetch_json('/api/version')
		if code != 200 or not version_info.get('ok', True):
			return 0
		if not version_info.get('update_enabled', True):
			return 0
		if not version_info.get('update_on_startup', True):
			return 0
	return run_update_flow(interactive = True, manual = manual)


if __name__ == '__main__':
	sys.exit(main())
