#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""绿色包启动门：试用走开关，付费必须联网校验。"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk

from lianhuan_client import TIMEOUT, api_base, http_request


def register_url() -> str:
	return api_base().rstrip('/') + '/register'


def post_json(path : str, payload : dict | None = None) -> tuple[int, dict]:
	url = api_base() + path
	data = None if payload is None else json.dumps(payload).encode('utf-8')
	try:
		with http_request(url, data = data, method = 'POST' if payload is not None else 'GET') as response:
			body = json.loads(response.read().decode('utf-8'))
			return response.status, body
	except urllib.error.HTTPError as error:
		try:
			body = json.loads(error.read().decode('utf-8'))
		except Exception:
			reason = '服务器拒绝访问。' if error.code == 403 else '服务器返回错误。'
			body = {'ok': False, 'reason': reason}
		return error.code, body
	except Exception:
		return 0, {'ok': False, 'reason': '连不上服务器。付费和试用都需要联网。'}


def get_json(path : str) -> tuple[int, dict]:
	url = api_base() + path
	try:
		with http_request(url) as response:
			body = json.loads(response.read().decode('utf-8'))
			return response.status, body
	except Exception:
		return 0, {'ok': False, 'reason': '连不上服务器。付费和试用都需要联网。'}


class LoginApp:
	def __init__(self) -> None:
		self.ok = False
		self.root = tk.Tk()
		self.root.title('脸幻')
		self.root.resizable(False, False)
		self.root.geometry('420x390')
		pad = ttk.Frame(self.root, padding = 20)
		pad.pack(fill = 'both', expand = True)

		ttk.Label(pad, text = '脸幻', font = ('Microsoft YaHei UI', 18, 'bold')).pack(anchor = 'w')
		ttk.Label(pad, text = '试用全部功能、不限天数。试用是否开放由后台开关决定。付费登录必须联网。', wraplength = 360).pack(anchor = 'w', pady = (8, 16))

		self.trial_btn = ttk.Button(pad, text = '免费试用', command = self.trial)
		self.trial_btn.pack(fill = 'x', ipady = 8)

		ttk.Separator(pad).pack(fill = 'x', pady = 16)
		account_row = ttk.Frame(pad)
		account_row.pack(fill = 'x')
		ttk.Label(account_row, text = '已有账号（网站注册的邮箱）').pack(side = 'left')
		register_link = tk.Label(
			account_row,
			text = '去网站注册',
			fg = '#4da3ff',
			cursor = 'hand2',
			font = ('Microsoft YaHei UI', 9)
		)
		register_link.pack(side = 'right')
		register_link.bind('<Button-1>', lambda _ : self.open_register())
		self.email = ttk.Entry(pad)
		self.email.pack(fill = 'x', pady = 4)
		self.password = ttk.Entry(pad, show = '*')
		self.password.pack(fill = 'x', pady = 4)
		ttk.Button(pad, text = '付费登录', command = self.login).pack(fill = 'x', pady = (8, 4))

		self.status = ttk.Label(pad, text = '', foreground = '#8a160f', wraplength = 360)
		self.status.pack(anchor = 'w', pady = (12, 0))
		self.root.bind('<Return>', lambda _ : self.login())

	def open_register(self) -> None:
		webbrowser.open(register_url())

	def set_status(self, text : str) -> None:
		self.status.config(text = text)
		self.root.update_idletasks()

	def succeed(self) -> None:
		self.ok = True
		self.root.destroy()

	def trial(self) -> None:
		self.set_status('正在连接…')
		code, body = post_json('/api/trial/start', {})
		if code == 200 and body.get('ok'):
			self.succeed()
			return
		self.set_status(str(body.get('reason') or '试用不可用。'))

	def login(self) -> None:
		email = self.email.get().strip()
		password = self.password.get()
		if not email or not password:
			self.set_status('请填写邮箱和密码。')
			return
		self.set_status('正在登录…')
		code, body = post_json('/api/login', {'email': email, 'password': password})
		if code == 200 and body.get('ok'):
			self.succeed()
			return
		self.set_status(str(body.get('reason') or '登录失败。'))

	def run(self) -> bool:
		self.root.mainloop()
		return self.ok


def main() -> int:
	if '--check' in sys.argv:
		code, body = get_json('/api/trial')
		print(json.dumps({'api': api_base(), 'status': code, 'body': body}, ensure_ascii = False))
		return 0 if code else 1
	app = LoginApp()
	return 0 if app.run() else 1


if __name__ == '__main__':
	sys.exit(main())
