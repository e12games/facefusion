#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""启动前检查更新：增量下载 internal/app 文件，失败可回滚。"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import urllib.request
from pathlib import Path

from lianhuan_client import (
	TIMEOUT,
	api_base,
	app_dir,
	fetch_json,
	package_root,
	read_local_version,
	update_dir,
	version_gt
)


BLOCKED_PREFIXES = (
	'.assets/models/',
	'.assets\\models\\',
)


def is_allowed_path(relative : str) -> bool:
	relative = relative.replace('\\', '/').lstrip('/')
	if not relative or relative.startswith('..'):
		return False
	for blocked in BLOCKED_PREFIXES:
		if relative.startswith(blocked):
			return False
	return True


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


def ask_update(latest : str, notes : str) -> bool:
	try:
		import tkinter as tk
		from tkinter import messagebox
		root = tk.Tk()
		root.withdraw()
		message = f'发现新版本 {latest}。'
		if notes.strip():
			message += f'\n\n{notes.strip()}'
		message += '\n\n是否现在更新？（不强制，选「否」可继续启动）'
		answer = messagebox.askyesno('脸幻 · 更新', message)
		root.destroy()
		return answer
	except Exception:
		return False


def download_file(url : str, dest : Path) -> None:
	dest.parent.mkdir(parents = True, exist_ok = True)
	request = urllib.request.Request(url, method = 'GET')
	with urllib.request.urlopen(request, timeout = TIMEOUT) as response, dest.open('wb') as handle:
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
		return
	backup_root = work_dir / 'backup' / version
	staging_root = work_dir / 'staging' / version
	pending_root = work_dir / 'pending' / version
	base = api_base().rstrip('/')

	for folder in (backup_root, staging_root, pending_root):
		if folder.exists():
			shutil.rmtree(folder)
		folder.mkdir(parents = True, exist_ok = True)

	backed_up : list[tuple[Path, str]] = []
	try:
		for item in files:
			relative = str(item.get('path') or '').replace('\\', '/').lstrip('/')
			if not is_allowed_path(relative):
				raise RuntimeError(f'不允许更新的路径：{relative}')
			expected_hash = str(item.get('sha256') or '').lower()
			expected_size = int(item.get('size') or 0)
			url = str(item.get('url') or f'{base}/releases/files/{relative}')
			target = app_path / relative.replace('/', '\\')
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
			target = app_path / relative.replace('/', '\\')
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


def main() -> int:
	root = package_root()
	app_path = app_dir(root)
	work_dir = update_dir(root)
	work_dir.mkdir(parents = True, exist_ok = True)
	state_path = work_dir / 'state.json'

	current = read_local_version(app_path)
	if load_state(state_path).get('version'):
		current = str(load_state(state_path).get('version'))

	if '--check-only' in sys.argv:
		code, body = fetch_json('/api/version')
		print(json.dumps({'local': current, 'remote': body, 'status': code}, ensure_ascii = False))
		return 0 if code else 1

	code, version_info = fetch_json('/api/version')
	if code != 200 or not version_info.get('ok', True):
		return 0
	if not version_info.get('update_enabled', True):
		return 0

	latest = str(version_info.get('version') or version_info.get('recommended_version') or '').strip()
	notes = str(version_info.get('notes') or '')
	if not latest or not version_gt(latest, current):
		return 0

	code, manifest = fetch_json(f'/api/update/manifest?current={current}')
	if code != 200 or not manifest.get('files'):
		return 0
	if not ask_update(latest, notes or str(manifest.get('notes') or '')):
		return 0

	try:
		apply_manifest(manifest, app_path, work_dir)
		save_state(state_path, latest)
		version_file = app_path / 'lianhuan_version.txt'
		version_file.write_text(latest + '\n', encoding = 'utf-8')
	except Exception as error:
		show_error(f'更新失败，已尝试恢复。\n{error}')
		return 1
	return 0


if __name__ == '__main__':
	sys.exit(main())
