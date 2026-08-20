#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""脸幻统一启动器：绿色包用 脸幻.exe，开发环境用 python lianhuan_launcher.py。"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def package_root() -> Path:
	if getattr(sys, 'frozen', False):
		return Path(sys.executable).resolve().parent
	return Path(__file__).resolve().parent


def is_portable(root : Path) -> bool:
	return (root / 'internal' / 'runtime' / 'python.exe').is_file()


def portable_paths(root : Path) -> tuple[Path, Path, Path]:
	runtime = root / 'internal' / 'runtime'
	app = root / 'internal' / 'app'
	ffmpeg = root / 'internal' / 'ffmpeg'
	return runtime, app, ffmpeg


def build_env(base : dict[str, str], prepend_paths : list[Path]) -> dict[str, str]:
	env = base.copy()
	env['FACEFUSION_LANGUAGE'] = 'zh'
	env['PYTHONNOUSERSITE'] = '1'
	parts = [ str(path) for path in prepend_paths if path.is_dir() ] + [ env.get('PATH', '') ]
	env['PATH'] = os.pathsep.join(parts)
	return env


def run_conda_unpack(runtime : Path) -> None:
	unpack = runtime / 'Scripts' / 'conda-unpack.exe'
	marker = runtime / '.unpacked'
	if unpack.is_file() and not marker.is_file():
		subprocess.run([ str(unpack) ], cwd = str(runtime), check = True)
		marker.write_text('1', encoding = 'utf-8')


def run_login(app_dir : Path, python : Path, env : dict[str, str]) -> bool:
	result = subprocess.run(
		[ str(python), 'lianhuan_login.py' ],
		cwd = str(app_dir),
		env = env
	)
	return result.returncode == 0


def run_facefusion(app_dir : Path, python : Path, env : dict[str, str]) -> int:
	creationflags = 0
	if os.name == 'nt':
		creationflags = subprocess.CREATE_NEW_CONSOLE
	return subprocess.run(
		[ str(python), 'facefusion.py', 'run', '--open-browser', '--language', 'zh' ],
		cwd = str(app_dir),
		env = env,
		creationflags = creationflags
	).returncode


def show_error(message : str) -> None:
	try:
		import tkinter as tk
		from tkinter import messagebox
		root = tk.Tk()
		root.withdraw()
		messagebox.showerror('脸幻', message)
		root.destroy()
	except Exception:
		print(message, file = sys.stderr)
		if os.name == 'nt':
			os.system('pause')


def launch_portable(root : Path) -> int:
	runtime, app, ffmpeg = portable_paths(root)
	if not app.is_dir():
		show_error('缺少程序文件，请重新安装或解压完整包。')
		return 1
	env = build_env(os.environ, [ runtime, runtime / 'Scripts', ffmpeg ])
	try:
		run_conda_unpack(runtime)
	except subprocess.CalledProcessError:
		show_error('首次解压运行环境失败，请关闭杀毒软件后重试。')
		return 1
	python = runtime / 'python.exe'
	if not run_login(app, python, env):
		return 1
	return run_facefusion(app, python, env)


def launch_dev(root : Path) -> int:
	winget_links = Path(os.environ.get('LOCALAPPDATA', '')) / 'Microsoft' / 'WinGet' / 'Links'
	prepend = [ winget_links ] if (winget_links / 'ffmpeg.exe').is_file() else []
	env = build_env(os.environ, prepend)
	python = Path(sys.executable)
	if not run_login(root, python, env):
		return 1
	return run_facefusion(root, python, env)


def main() -> int:
	root = package_root()
	os.chdir(root)
	try:
		if is_portable(root):
			return launch_portable(root)
		return launch_dev(root)
	except FileNotFoundError:
		show_error('找不到 Python 或主程序，请检查安装是否完整。')
		return 1


if __name__ == '__main__':
	sys.exit(main())
