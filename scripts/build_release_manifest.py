#!/usr/bin/env python3
"""扫描 web/releases/files 生成 manifest.json（路径相对 internal/app）。"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES_DIR = ROOT / 'web' / 'releases' / 'files'
MANIFEST_PATH = ROOT / 'web' / 'releases' / 'manifest.json'


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
		return 1
	payload = build(version, notes)
	print(json.dumps(payload, ensure_ascii = False, indent = 2))
	print(f'已写入 {MANIFEST_PATH}')
	return 0


if __name__ == '__main__':
	sys.exit(main())
