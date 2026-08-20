#!/usr/bin/env python3
"""扫描 releases/files 生成 manifest.json（路径相对 internal/app）。"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES_DIR = ROOT / 'releases' / 'files'
MANIFEST_PATH = ROOT / 'releases' / 'manifest.json'

BLOCKED_UPDATE_PREFIXES = (
	'.assets/models/',
	'runtime/',
)


def normalize_update_path(relative : str) -> str:
	return relative.replace('\\', '/').lstrip('/')


def is_allowed_update_path(relative : str) -> bool:
	relative = normalize_update_path(relative)
	if not relative:
		return False
	if relative.startswith('/') or __import__('re').match(r'^[A-Za-z]:', relative):
		return False
	parts = relative.split('/')
	if any(part in ('', '.', '..') for part in parts):
		return False
	for blocked in BLOCKED_UPDATE_PREFIXES:
		if relative.startswith(blocked):
			return False
	return True


def sha256_file(path : Path) -> str:
	digest = hashlib.sha256()
	with path.open('rb') as handle:
		for chunk in iter(lambda: handle.read(1024 * 1024), b''):
			digest.update(chunk)
	return digest.hexdigest()


def build(version : str, notes : str) -> dict:
	files : list[dict] = []
	if FILES_DIR.is_dir():
		for path in sorted(FILES_DIR.rglob('*')):
			if not path.is_file():
				continue
			relative = path.relative_to(FILES_DIR).as_posix()
			if path.name.startswith('.'):
				continue
			if not is_allowed_update_path(relative):
				print(f'跳过不允许的路径：{relative}', file = sys.stderr)
				continue
			files.append({
				'path': relative,
				'sha256': sha256_file(path),
				'size': path.stat().st_size
			})
	payload = {
		'version': version,
		'force': False,
		'notes': notes,
		'files': files
	}
	MANIFEST_PATH.parent.mkdir(parents = True, exist_ok = True)
	MANIFEST_PATH.write_text(json.dumps(payload, ensure_ascii = False, indent = 2) + '\n', encoding = 'utf-8')
	return payload


def main() -> int:
	version = sys.argv[1] if len(sys.argv) > 1 else ''
	notes = sys.argv[2] if len(sys.argv) > 2 else ''
	if not version:
		print('用法: python scripts/build_release_manifest.py 20260820 "更新说明"')
		print('文件目录: releases/files/  →  推送到 facefusion-releases 公开仓')
		return 1
	payload = build(version, notes)
	print(json.dumps(payload, ensure_ascii = False, indent = 2))
	print(f'已写入 {MANIFEST_PATH}')
	print('下一步: bash scripts/publish_releases_repo.sh')
	return 0


if __name__ == '__main__':
	sys.exit(main())
