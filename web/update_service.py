#!/usr/bin/env python3
"""服务端：版本号、manifest 读取与组装（公开仓 facefusion-releases）。"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote

WEB_ROOT = Path(__file__).resolve().parent
VERSION_RE = re.compile(r'^(\d{8})(?:\.(\d+))?$')
DEFAULT_RELEASES_REPO = 'https://github.com/e12games/facefusion-releases.git'
DEFAULT_RELEASES_RAW = 'https://raw.githubusercontent.com/e12games/facefusion-releases/main'
FETCH_UA = 'Mozilla/5.0 (compatible; LianHuan/1)'

BLOCKED_UPDATE_PREFIXES = (
	'.assets/models/',
	'runtime/',
)


def releases_repo_url() -> str:
	return os.environ.get('LIANHUAN_RELEASES_REPO', DEFAULT_RELEASES_REPO).strip() or DEFAULT_RELEASES_REPO


def releases_raw_base() -> str:
	return os.environ.get('LIANHUAN_RELEASES_RAW_BASE', DEFAULT_RELEASES_RAW).strip().rstrip('/') or DEFAULT_RELEASES_RAW


def releases_dir() -> Path:
	env = os.environ.get('LIANHUAN_RELEASES_DIR', '').strip()
	if env:
		return Path(env)
	repo_releases = WEB_ROOT.parent / 'releases'
	if repo_releases.is_dir():
		return repo_releases
	return Path('/opt/lianhuan/releases')


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


def normalize_manifest(data : Any) -> dict[str, Any]:
	if not isinstance(data, dict):
		data = {}
	data.setdefault('version', default_version())
	data.setdefault('force', False)
	data.setdefault('notes', '')
	data.setdefault('files', [])
	return data


def fetch_remote_manifest() -> Optional[dict[str, Any]]:
	url = releases_raw_base() + '/manifest.json'
	request = urllib.request.Request(url, headers = {'User-Agent': FETCH_UA})
	try:
		with urllib.request.urlopen(request, timeout = 20) as response:
			return normalize_manifest(json.loads(response.read().decode('utf-8')))
	except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError):
		return None


def load_manifest_local() -> dict[str, Any]:
	path = manifest_path()
	if not path.is_file():
		return {'version': default_version(), 'force': False, 'notes': '', 'files': []}
	try:
		data = json.loads(path.read_text(encoding = 'utf-8'))
	except Exception:
		data = {}
	return normalize_manifest(data)


def load_manifest() -> dict[str, Any]:
	remote = fetch_remote_manifest()
	if remote is not None:
		return remote
	return load_manifest_local()


def save_manifest(data : dict[str, Any]) -> None:
	root = releases_dir()
	root.mkdir(parents = True, exist_ok = True)
	files_dir().mkdir(parents = True, exist_ok = True)
	manifest_path().write_text(json.dumps(data, ensure_ascii = False, indent = 2) + '\n', encoding = 'utf-8')


def file_download_url(relative : str, site_base_url : str = '') -> str:
	"""客户端一律从公开仓 GitHub Raw 下载，不走站点 /releases/。"""
	relative = normalize_update_path(relative)
	return releases_raw_base() + '/files/' + quote(relative, safe = '/')


def manifest_for_client(current : str, base_url : str, update_enabled : bool) -> dict[str, Any]:
	manifest = load_manifest()
	latest = str(manifest.get('version') or default_version())
	payload : dict[str, Any] = {
		'ok': True,
		'version': latest,
		'force': False,
		'notes': manifest.get('notes') or '',
		'files': [],
		'releases_source': releases_raw_base(),
		'releases_repo': releases_repo_url()
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
		sha = str(item.get('sha256') or '').lower()
		if not sha:
			continue
		file_path = fdir / relative.replace('/', os.sep)
		size = int(item.get('size') or 0)
		if not size and file_path.is_file():
			size = file_path.stat().st_size
		files.append({
			'path': relative,
			'sha256': sha,
			'size': size,
			'url': file_download_url(relative)
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
		'update_on_startup': update_on_startup,
		'releases_source': releases_raw_base(),
		'releases_repo': releases_repo_url()
	}
