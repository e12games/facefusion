#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""脸幻客户端共用：路径、API 地址、版本比较。"""
from __future__ import annotations

import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


TIMEOUT = 30
VERSION_RE = re.compile(r'^(\d{8})(?:\.(\d+))?$')
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) LianHuan/1'


def package_root() -> Path:
	start = Path(__file__).resolve().parent
	if getattr(__import__('sys'), 'frozen', False):
		start = Path(__import__('sys').executable).resolve().parent
	for candidate in (start, start.parent, start.parent.parent):
		if (candidate / 'internal' / 'runtime' / 'python.exe').is_file():
			return candidate
		if (candidate / 'facefusion.py').is_file():
			return candidate
	return start


def app_dir(root : Path | None = None) -> Path:
	root = root or package_root()
	portable = root / 'internal' / 'app'
	if portable.is_dir() and (root / 'internal' / 'runtime').is_dir():
		return portable
	return root


def update_dir(root : Path | None = None) -> Path:
	root = root or package_root()
	if (root / 'internal' / 'app').is_dir() and (root / 'internal' / 'runtime').is_dir():
		return root / 'internal' / 'update'
	return root / 'update'


def api_base() -> str:
	env = os.environ.get('LIANHUAN_API', '').strip().rstrip('/')
	if env:
		return env
	root = package_root()
	candidates = [
		root / 'lianhuan_api.txt',
		root / 'internal' / 'app' / 'lianhuan_api.txt',
		Path(__file__).resolve().parent / 'lianhuan_api.txt',
		Path.cwd() / 'lianhuan_api.txt'
	]
	for candidate in candidates:
		if candidate.is_file():
			for line in candidate.read_text(encoding = 'utf-8', errors = 'ignore').splitlines():
				line = line.strip()
				if line and not line.startswith('#'):
					return line.rstrip('/')
	return 'https://facefusion.iqiyia.cyou'


def http_request(url : str, data : bytes | None = None, method : str | None = None):
	headers = {'User-Agent': USER_AGENT}
	if data is not None:
		headers['Content-Type'] = 'application/json'
	request = urllib.request.Request(url, data = data, method = method or ('POST' if data is not None else 'GET'), headers = headers)
	return urllib.request.urlopen(request, timeout = TIMEOUT)


def fetch_json(path : str) -> tuple[int, dict[str, Any]]:
	url = api_base().rstrip('/') + path
	try:
		with http_request(url) as response:
			import json
			body = json.loads(response.read().decode('utf-8'))
			return response.status, body if isinstance(body, dict) else {}
	except urllib.error.HTTPError as error:
		try:
			import json
			body = json.loads(error.read().decode('utf-8'))
		except Exception:
			body = {'ok': False, 'reason': '服务器返回错误。'}
		return error.code, body
	except Exception:
		return 0, {'ok': False, 'reason': '连不上更新服务器。'}


def parse_version(value : str) -> tuple[int, int]:
	value = (value or '').strip()
	match = VERSION_RE.match(value)
	if not match:
		return 0, 0
	return int(match.group(1)), int(match.group(2) or 0)


def version_gt(left : str, right : str) -> bool:
	return parse_version(left) > parse_version(right)


def version_gte(left : str, right : str) -> bool:
	return parse_version(left) >= parse_version(right)


def read_local_version(app_path : Path | None = None) -> str:
	app_path = app_path or app_dir()
	for candidate in (app_path / 'lianhuan_version.txt', update_dir() / 'state.json'):
		if candidate.name == 'state.json' and candidate.is_file():
			try:
				import json
				data = json.loads(candidate.read_text(encoding = 'utf-8'))
				version = str(data.get('version') or '').strip()
				if version:
					return version
			except Exception:
				pass
		if candidate.name == 'lianhuan_version.txt' and candidate.is_file():
			for line in candidate.read_text(encoding = 'utf-8', errors = 'ignore').splitlines():
				line = line.strip()
				if line and not line.startswith('#'):
					return line
	return '0'
