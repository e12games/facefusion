#!/usr/bin/env python3
"""服务端：版本号、manifest 读取与组装。"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

WEB_ROOT = Path(__file__).resolve().parent
VERSION_RE = re.compile(r'^(\d{8})(?:\.(\d+))?$')

BLOCKED_UPDATE_PREFIXES = (
	'.assets/models/',
	'runtime/',
)


def releases_dir() -> Path:
	env = os.environ.get('LIANHUAN_RELEASES_DIR', '').strip()
	if env:
		return Path(env)
	repo_releases = WEB_ROOT.parent / 'releases'
	if repo_releases.is_dir():
		return repo_releases
	legacy = WEB_ROOT / 'releases'
	return legacy


def manifest_path() -> Path:
	return releases_dir() / 'manifest.json'


def files_dir() -> Path:
	return releases_dir() / 'files'


def normalize_update_path(relative : str) -> str:
	return relative.replace('\\', '/').lstrip('/')


def is_allowed_update_path(relative : str) -> bool:
	relative = normalize_update_path(relative)
	if not relative:
		return False
	if relative.startswith('/') or re.match(r'^[A-Za-z]:', relative):
		return False
	parts = relative.split('/')
	if any(part in ('', '.', '..') for part in parts):
		return False
	for blocked in BLOCKED_UPDATE_PREFIXES:
		if relative.startswith(blocked):
			return False
	return True


def default_version() -> str:
	return datetime.now(timezone.utc).strftime('%Y%m%d')


def parse_version(value : str) -> tuple[int, int]:
	value = (value or '').strip()
	match = VERSION_RE.match(value)
	if not match:
		return 0, 0
	return int(match.group(1)), int(match.group(2) or 0)


def version_gt(left : str, right : str) -> bool:
	return parse_version(left) > parse_version(right)


def load_manifest() -> dict[str, Any]:
	path = manifest_path()
	if not path.is_file():
		return {'version': default_version(), 'force': False, 'notes': '', 'files': []}
	try:
		data = json.loads(path.read_text(encoding = 'utf-8'))
	except Exception:
		data = {}
	if not isinstance(data, dict):
		data = {}
	data.setdefault('version', default_version())
	data.setdefault('force', False)
	data.setdefault('notes', '')
	data.setdefault('files', [])
	return data


def save_manifest(data : dict[str, Any]) -> None:
	root = releases_dir()
	root.mkdir(parents = True, exist_ok = True)
	files_dir().mkdir(parents = True, exist_ok = True)
	manifest_path().write_text(json.dumps(data, ensure_ascii = False, indent = 2) + '\n', encoding = 'utf-8')


def manifest_for_client(current : str, base_url : str, update_enabled : bool) -> dict[str, Any]:
	manifest = load_manifest()
	latest = str(manifest.get('version') or default_version())
	payload : dict[str, Any] = {
		'ok': True,
		'version': latest,
		'force': False,
		'notes': manifest.get('notes') or '',
		'files': []
	}
	if not update_enabled:
		return payload
	if current and not version_gt(latest, current):
		return payload
	files : list[dict[str, Any]] = []
	fdir = files_dir()
	for item in manifest.get('files') or []:
		if not isinstance(item, dict):
			continue
		relative = str(item.get('path') or '').replace('\\', '/').lstrip('/')
		if not relative or not is_allowed_update_path(relative):
			continue
		file_path = fdir / relative.replace('/', os.sep)
		if not file_path.is_file():
			continue
		url = base_url.rstrip('/') + '/releases/files/' + quote(relative.replace('\\', '/'), safe = '/')
		files.append({
			'path': relative,
			'sha256': item.get('sha256') or '',
			'size': item.get('size') or file_path.stat().st_size,
			'url': url
		})
	payload['files'] = files
	return payload


def version_payload(
	app_version : str,
	release_notes : str,
	update_enabled : bool,
	update_on_startup : bool = True
) -> dict[str, Any]:
	manifest = load_manifest()
	latest = app_version or str(manifest.get('version') or default_version())
	return {
		'ok': True,
		'version': latest,
		'recommended_version': latest,
		'force': False,
		'notes': release_notes or str(manifest.get('notes') or ''),
		'update_enabled': update_enabled,
		'update_on_startup': update_on_startup
	}
