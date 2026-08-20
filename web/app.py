#!/usr/bin/env python3
import os
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import pbkdf2_hmac
from pathlib import Path
from secrets import token_hex
from typing import Any, Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.middleware.sessions import SessionMiddleware

from update_service import default_version, load_manifest, manifest_for_client, save_manifest, version_payload
from payment_service import normalize_tx_hash, verify_trc20_usdt

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / 'data'
DB_PATH = DATA_DIR / 'lianhuan.db'
RELEASES_DIR = ROOT / 'releases'
SECRET = os.environ.get('LIANHUAN_SECRET', 'lianhuan-dev-secret-change-me')
ADMIN_EMAIL = os.environ.get('LIANHUAN_ADMIN_EMAIL', 'admin@local.test').strip().lower()
ADMIN_PASSWORD = os.environ.get('LIANHUAN_ADMIN_PASSWORD', 'admin123')
VERSION_RE = re.compile(r'^(\d{8})(?:\.(\d+))?$')

app = FastAPI(title = '脸幻')
app.add_middleware(SessionMiddleware, secret_key = SECRET, session_cookie = 'lianhuan_session')
app.mount('/static', StaticFiles(directory = str(ROOT / 'static')), name = 'static')
if RELEASES_DIR.is_dir():
	app.mount('/releases', StaticFiles(directory = str(RELEASES_DIR)), name = 'releases')
jinja_env = Environment(
	loader = FileSystemLoader(str(ROOT / 'templates')),
	autoescape = select_autoescape(['html', 'xml'])
)


def row_dict(row : Optional[sqlite3.Row]) -> Optional[dict[str, Any]]:
	if row is None:
		return None
	return dict(row)


def utc_now() -> str:
	return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')


def hash_password(password : str, salt : Optional[str] = None) -> str:
	salt = salt or token_hex(16)
	digest = pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 120000).hex()
	return salt + '$' + digest


def verify_password(password : str, stored : str) -> bool:
	if '$' not in stored:
		return False
	salt, _ = stored.split('$', 1)
	return stored == hash_password(password, salt)


def get_db() -> sqlite3.Connection:
	DATA_DIR.mkdir(parents = True, exist_ok = True)
	connection = sqlite3.connect(DB_PATH)
	connection.row_factory = sqlite3.Row
	return connection


def init_db() -> None:
	with closing(get_db()) as connection:
		connection.executescript(
			'''
			CREATE TABLE IF NOT EXISTS settings (
				key TEXT PRIMARY KEY,
				value TEXT NOT NULL
			);
			CREATE TABLE IF NOT EXISTS users (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				email TEXT NOT NULL UNIQUE,
				password_hash TEXT NOT NULL,
				is_admin INTEGER NOT NULL DEFAULT 0,
				is_paid INTEGER NOT NULL DEFAULT 0,
				created_at TEXT NOT NULL
			);
			CREATE TABLE IF NOT EXISTS orders (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				user_id INTEGER NOT NULL,
				email TEXT NOT NULL,
				amount_usdt TEXT NOT NULL,
				tx_hash TEXT,
				status TEXT NOT NULL,
				note TEXT NOT NULL DEFAULT '',
				created_at TEXT NOT NULL,
				paid_at TEXT,
				FOREIGN KEY(user_id) REFERENCES users(id)
			);
			CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_tx ON orders(tx_hash) WHERE tx_hash IS NOT NULL AND tx_hash != '';
			'''
		)
		if connection.execute('SELECT 1 FROM settings WHERE key = ?', ('trial_enabled',)).fetchone() is None:
			connection.execute('INSERT INTO settings(key, value) VALUES (?, ?)', ('trial_enabled', '1'))
		defaults = {
			'app_version': default_version(),
			'release_notes': '',
			'update_enabled': '1',
			'usdt_trc20_wallet': '',
			'membership_price_usdt': '29'
		}
		for key, value in defaults.items():
			if connection.execute('SELECT 1 FROM settings WHERE key = ?', (key,)).fetchone() is None:
				connection.execute('INSERT INTO settings(key, value) VALUES (?, ?)', (key, value))
		admin = connection.execute('SELECT id FROM users WHERE email = ?', (ADMIN_EMAIL,)).fetchone()
		if admin is None:
			connection.execute(
				'INSERT INTO users(email, password_hash, is_admin, is_paid, created_at) VALUES (?, ?, 1, 1, ?)',
				(ADMIN_EMAIL, hash_password(ADMIN_PASSWORD), utc_now())
			)
		else:
			connection.execute(
				'UPDATE users SET password_hash = ?, is_admin = 1, is_paid = 1 WHERE email = ?',
				(hash_password(ADMIN_PASSWORD), ADMIN_EMAIL)
			)
		connection.execute('UPDATE users SET is_admin = 0 WHERE email != ? AND is_admin = 1', (ADMIN_EMAIL,))
		connection.commit()


def setting(key : str, fallback : str = '') -> str:
	with closing(get_db()) as connection:
		row = connection.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
	return row['value'] if row else fallback


def set_setting(key : str, value : str) -> None:
	with closing(get_db()) as connection:
		connection.execute('INSERT INTO settings(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value', (key, value))
		connection.commit()


def get_user_by_email(email : str) -> Optional[dict[str, Any]]:
	with closing(get_db()) as connection:
		return row_dict(connection.execute('SELECT * FROM users WHERE email = ?', (email.strip().lower(),)).fetchone())


def current_user(request : Request) -> Optional[dict[str, Any]]:
	email = request.session.get('email')
	if not email:
		return None
	return get_user_by_email(email)


def render(request : Request, name : str, extra : Optional[dict[str, Any]] = None):
	payload = {
		'request': request,
		'user': current_user(request),
		'trial_enabled': setting('trial_enabled') == '1',
		'membership_price_usdt': setting('membership_price_usdt', '29')
	}
	if extra:
		payload.update(extra)
	html = jinja_env.get_template(name).render(**payload)
	return HTMLResponse(html)


def mark_user_paid(user_id : int) -> None:
	with closing(get_db()) as connection:
		connection.execute('UPDATE users SET is_paid = 1 WHERE id = ?', (user_id,))
		connection.commit()


def complete_order(order_id : int, note : str = '') -> None:
	with closing(get_db()) as connection:
		row = connection.execute('SELECT user_id FROM orders WHERE id = ?', (order_id,)).fetchone()
		if not row:
			return
		connection.execute(
			'UPDATE orders SET status = ?, note = ?, paid_at = ? WHERE id = ?',
			('paid', note, utc_now(), order_id)
		)
		connection.execute('UPDATE users SET is_paid = 1 WHERE id = ?', (row['user_id'],))
		connection.commit()


@app.on_event('startup')
def on_startup() -> None:
	init_db()


@app.api_route('/', methods = ['GET', 'HEAD'])
def home(request : Request):
	return render(request, 'index.html')


@app.get('/register')
def register_page(request : Request):
	if current_user(request):
		return RedirectResponse('/', status_code = 303)
	return render(request, 'register.html', {'error': ''})


@app.post('/register')
def register(request : Request, email : str = Form(...), password : str = Form(...), password2 : str = Form(...)):
	email = email.strip().lower()
	error = ''
	if '@' not in email or '.' not in email:
		error = '请填写有效邮箱。'
	elif len(password) < 6:
		error = '密码至少 6 位。'
	elif password != password2:
		error = '两次密码不一致。'
	elif get_user_by_email(email):
		error = '该邮箱已注册。'
	if error:
		return render(request, 'register.html', {'error': error, 'email': email})
	with closing(get_db()) as connection:
		connection.execute(
			'INSERT INTO users(email, password_hash, is_admin, is_paid, created_at) VALUES (?, ?, 0, 0, ?)',
			(email, hash_password(password), utc_now())
		)
		connection.commit()
	request.session['email'] = email
	return RedirectResponse('/', status_code = 303)


@app.get('/login')
def login_page(request : Request):
	if current_user(request):
		return RedirectResponse('/', status_code = 303)
	return render(request, 'login.html', {'error': ''})


@app.post('/login')
def login(request : Request, email : str = Form(...), password : str = Form(...)):
	email = email.strip().lower()
	user = get_user_by_email(email)
	if not user or not verify_password(password, user['password_hash']):
		return render(request, 'login.html', {'error': '邮箱或密码不对。', 'email': email})
	request.session['email'] = email
	if user['is_admin']:
		return RedirectResponse('/admin', status_code = 303)
	return RedirectResponse('/', status_code = 303)


@app.get('/logout')
def logout(request : Request):
	request.session.clear()
	return RedirectResponse('/', status_code = 303)


@app.get('/buy')
def buy_page(request : Request):
	user = current_user(request)
	if not user:
		return RedirectResponse('/login', status_code = 303)
	if user['is_admin'] or user['is_paid']:
		return RedirectResponse('/', status_code = 303)
	wallet = setting('usdt_trc20_wallet', '')
	price = setting('membership_price_usdt', '29')
	with closing(get_db()) as connection:
		orders = [
			dict(row) for row in connection.execute(
				'SELECT id, amount_usdt, tx_hash, status, note, created_at, paid_at FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 10',
				(user['id'],)
			).fetchall()
		]
	return render(request, 'buy.html', {
		'wallet': wallet,
		'price': price,
		'orders': orders,
		'error': '',
		'message': ''
	})


@app.post('/buy')
def buy_submit(request : Request, tx_hash : str = Form(...)):
	user = current_user(request)
	if not user:
		return RedirectResponse('/login', status_code = 303)
	if user['is_admin'] or user['is_paid']:
		return RedirectResponse('/', status_code = 303)
	wallet = setting('usdt_trc20_wallet', '').strip()
	price = setting('membership_price_usdt', '29').strip() or '29'
	tx_hash_norm = normalize_tx_hash(tx_hash)
	error = ''
	message = ''
	if not wallet:
		error = '收款地址尚未配置，请稍后再试或联系管理员。'
	elif not tx_hash_norm or len(tx_hash_norm) != 64:
		error = '请填写有效的 TRC20 交易哈希。'
	else:
		with closing(get_db()) as connection:
			exists = connection.execute('SELECT id FROM orders WHERE tx_hash = ?', (tx_hash_norm,)).fetchone()
		if exists:
			error = '该交易哈希已提交过。'
		else:
			min_amount = Decimal(price)
			ok, verify_note = verify_trc20_usdt(tx_hash_norm, wallet, min_amount)
			status = 'paid' if ok else 'pending'
			with closing(get_db()) as connection:
				connection.execute(
					'INSERT INTO orders(user_id, email, amount_usdt, tx_hash, status, note, created_at, paid_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
					(
						user['id'], user['email'], price, tx_hash_norm, status, verify_note, utc_now(),
						utc_now() if ok else None
					)
				)
				if ok:
					connection.execute('UPDATE users SET is_paid = 1 WHERE id = ?', (user['id'],))
				connection.commit()
			if ok:
				message = '支付已确认，会员已开通。请重新打开客户端，用邮箱登录。'
			else:
				message = '已收到提交。链上暂未自动确认，管理员会人工核对；通过后即可登录付费版。'
	with closing(get_db()) as connection:
		orders = [
			dict(row) for row in connection.execute(
				'SELECT id, amount_usdt, tx_hash, status, note, created_at, paid_at FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 10',
				(user['id'],)
			).fetchall()
		]
	return render(request, 'buy.html', {
		'wallet': wallet,
		'price': price,
		'orders': orders,
		'error': error,
		'message': message
	})


@app.get('/admin')
def admin_page(request : Request):
	user = current_user(request)
	if not user or not user['is_admin']:
		return RedirectResponse('/login', status_code = 303)
	with closing(get_db()) as connection:
		users = [ dict(row) for row in connection.execute('SELECT id, email, is_admin, is_paid, created_at FROM users ORDER BY id DESC').fetchall() ]
	manifest = load_manifest()
	with closing(get_db()) as connection:
		pending_orders = [
			dict(row) for row in connection.execute(
				'''
				SELECT orders.id, orders.email, orders.amount_usdt, orders.tx_hash, orders.status, orders.note, orders.created_at, orders.paid_at
				FROM orders ORDER BY orders.id DESC LIMIT 50
				'''
			).fetchall()
		]
	return render(request, 'admin.html', {
		'users': users,
		'message': '',
		'app_version': setting('app_version', default_version()),
		'release_notes': setting('release_notes', ''),
		'update_enabled': setting('update_enabled', '1') == '1',
		'manifest_version': manifest.get('version', ''),
		'manifest_files': len(manifest.get('files') or []),
		'usdt_trc20_wallet': setting('usdt_trc20_wallet', ''),
		'membership_price_usdt': setting('membership_price_usdt', '29'),
		'orders': pending_orders
	})


@app.post('/admin/trial')
def admin_trial(request : Request, trial_enabled : Optional[str] = Form(None)):
	user = current_user(request)
	if not user or not user['is_admin']:
		return RedirectResponse('/login', status_code = 303)
	set_setting('trial_enabled', '1' if trial_enabled else '0')
	return RedirectResponse('/admin', status_code = 303)


@app.post('/admin/paid/{user_id}')
def admin_paid(request : Request, user_id : int, is_paid : str = Form(...)):
	user = current_user(request)
	if not user or not user['is_admin']:
		return RedirectResponse('/login', status_code = 303)
	with closing(get_db()) as connection:
		connection.execute('UPDATE users SET is_paid = ? WHERE id = ? AND is_admin = 0', (1 if is_paid == '1' else 0, user_id))
		connection.commit()
	return RedirectResponse('/admin', status_code = 303)


@app.post('/admin/payment')
def admin_payment(
	request : Request,
	usdt_trc20_wallet : str = Form(''),
	membership_price_usdt : str = Form('29')
):
	user = current_user(request)
	if not user or not user['is_admin']:
		return RedirectResponse('/login', status_code = 303)
	set_setting('usdt_trc20_wallet', usdt_trc20_wallet.strip())
	price = membership_price_usdt.strip() or '29'
	try:
		Decimal(price)
	except Exception:
		price = '29'
	set_setting('membership_price_usdt', price)
	return RedirectResponse('/admin', status_code = 303)


@app.post('/admin/order/{order_id}/approve')
def admin_order_approve(request : Request, order_id : int):
	user = current_user(request)
	if not user or not user['is_admin']:
		return RedirectResponse('/login', status_code = 303)
	complete_order(order_id, '管理员已确认到账。')
	return RedirectResponse('/admin', status_code = 303)


@app.post('/admin/order/{order_id}/reject')
def admin_order_reject(request : Request, order_id : int):
	user = current_user(request)
	if not user or not user['is_admin']:
		return RedirectResponse('/login', status_code = 303)
	with closing(get_db()) as connection:
		connection.execute(
			'UPDATE orders SET status = ?, note = ? WHERE id = ?',
			('rejected', '管理员已拒绝。', order_id)
		)
		connection.commit()
	return RedirectResponse('/admin', status_code = 303)


@app.post('/admin/release')
def admin_release(
	request : Request,
	app_version : str = Form(...),
	release_notes : str = Form(''),
	update_enabled : Optional[str] = Form(None),
	sync_manifest : Optional[str] = Form(None)
):
	user = current_user(request)
	if not user or not user['is_admin']:
		return RedirectResponse('/login', status_code = 303)
	version = app_version.strip()
	if not VERSION_RE.match(version):
		return RedirectResponse('/admin', status_code = 303)
	set_setting('app_version', version)
	set_setting('release_notes', release_notes.strip())
	set_setting('update_enabled', '1' if update_enabled else '0')
	if sync_manifest:
		manifest = load_manifest()
		manifest['version'] = version
		manifest['force'] = False
		manifest['notes'] = release_notes.strip()
		save_manifest(manifest)
	return RedirectResponse('/admin', status_code = 303)


@app.get('/api/version')
def api_version():
	return version_payload(
		setting('app_version', default_version()),
		setting('release_notes', ''),
		setting('update_enabled', '1') == '1'
	)


@app.get('/api/update/manifest')
def api_update_manifest(request : Request, current : str = ''):
	base_url = str(request.base_url).rstrip('/')
	return manifest_for_client(current.strip(), base_url, setting('update_enabled', '1') == '1')


@app.get('/api/trial')
def api_trial():
	return {'ok': True, 'trial_enabled': setting('trial_enabled') == '1'}


@app.post('/api/login')
async def api_login(request : Request):
	payload = await request.json()
	email = str(payload.get('email') or '').strip().lower()
	password = str(payload.get('password') or '')
	user = get_user_by_email(email)
	if not user or not verify_password(password, user['password_hash']):
		return JSONResponse({'ok': False, 'reason': '邮箱或密码不对。'}, status_code = 401)
	if user['is_admin'] or user['is_paid']:
		return {'ok': True, 'paid': True, 'email': user['email']}
	return JSONResponse({'ok': False, 'reason': '该账号尚未开通付费。请使用免费试用，或在网站购买会员。'}, status_code = 403)


@app.post('/api/trial/start')
def api_trial_start():
	if setting('trial_enabled') != '1':
		return JSONResponse({'ok': False, 'reason': '试用已暂停。'}, status_code = 403)
	return {'ok': True, 'trial': True}
