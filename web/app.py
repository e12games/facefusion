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

from update_service import default_version, load_manifest, manifest_for_client, releases_dir, save_manifest, version_payload
from payment_service import normalize_tx_hash, verify_trc20_usdt, wallet_qr_svg, SUPPORT_TELEGRAM
from web_deploy_service import apply_web_update, check_web_update, git_status, read_log_tail
from releases_deploy_service import check_releases, pull_releases, releases_status

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / 'data'
DB_PATH = DATA_DIR / 'lianhuan.db'
SECRET = os.environ.get('LIANHUAN_SECRET', 'lianhuan-dev-secret-change-me')
ADMIN_EMAIL = os.environ.get('LIANHUAN_ADMIN_EMAIL', 'admin@lianhuan.local').strip().lower()
ADMIN_PASSWORD = os.environ.get('LIANHUAN_ADMIN_PASSWORD', 'admin123')
VERSION_RE = re.compile(r'^(\d{8})(?:\.(\d+))?$')
DEFAULT_ADMIN_EMAIL = 'admin@lianhuan.local'
DEFAULT_ADMIN_PASSWORD = 'admin123'

app = FastAPI(title = '脸幻')
app.add_middleware(SessionMiddleware, secret_key = SECRET, session_cookie = 'lianhuan_session')
app.mount('/static', StaticFiles(directory = str(ROOT / 'static')), name = 'static')
_releases = releases_dir()
if _releases.is_dir():
	app.mount('/releases', StaticFiles(directory = str(_releases)), name = 'releases')
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
			'''
		)
		try:
			connection.execute(
				"CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_tx ON orders(tx_hash) WHERE tx_hash IS NOT NULL AND tx_hash != ''"
			)
		except sqlite3.OperationalError:
			pass
		try:
			connection.execute('ALTER TABLE users ADD COLUMN free_uses_remaining INTEGER NOT NULL DEFAULT 0')
		except sqlite3.OperationalError:
			pass
		if connection.execute('SELECT 1 FROM settings WHERE key = ?', ('trial_enabled',)).fetchone() is None:
			connection.execute('INSERT INTO settings(key, value) VALUES (?, ?)', ('trial_enabled', '1'))
		defaults = {
			'app_version': default_version(),
			'release_notes': '',
			'update_enabled': '1',
			'client_update_on_startup': '1',
			'usdt_trc20_wallet': '',
			'membership_price_usdt': '20',
			'admin_password_changed': '0',
			'register_code_required': '0',
			'register_code': '',
			'new_user_free_uses': '3',
			'legacy_free_uses_granted': '0'
		}
		for key, value in defaults.items():
			if connection.execute('SELECT 1 FROM settings WHERE key = ?', (key,)).fetchone() is None:
				connection.execute('INSERT INTO settings(key, value) VALUES (?, ?)', (key, value))
		admin = connection.execute('SELECT id FROM users WHERE email = ?', (ADMIN_EMAIL,)).fetchone()
		if admin is None:
			connection.execute(
				'INSERT INTO users(email, password_hash, is_admin, is_paid, free_uses_remaining, created_at) VALUES (?, ?, 1, 1, 0, ?)',
				(ADMIN_EMAIL, hash_password(ADMIN_PASSWORD), utc_now())
			)
		if connection.execute('SELECT 1 FROM settings WHERE key = ?', ('legacy_free_uses_granted',)).fetchone() is None:
			connection.execute('INSERT INTO settings(key, value) VALUES (?, ?)', ('legacy_free_uses_granted', '0'))
		if setting_in_connection(connection, 'legacy_free_uses_granted', '0') != '1':
			grant = parse_free_uses(setting_in_connection(connection, 'new_user_free_uses', '3'))
			connection.execute(
				'UPDATE users SET free_uses_remaining = ? WHERE is_admin = 0 AND is_paid = 0 AND free_uses_remaining = 0',
				(grant,)
			)
			connection.execute(
				'INSERT INTO settings(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value',
				('legacy_free_uses_granted', '1')
			)
		connection.commit()


def setting_in_connection(connection : sqlite3.Connection, key : str, fallback : str = '') -> str:
	row = connection.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
	return row['value'] if row else fallback


def parse_free_uses(value : str) -> int:
	try:
		count = int(str(value or '').strip())
	except Exception:
		count = 3
	return max(0, min(count, 999))


def new_user_free_uses() -> int:
	return parse_free_uses(setting('new_user_free_uses', '3'))


def register_code_required() -> bool:
	return setting('register_code_required', '0') == '1'


def validate_register_code(code : str) -> bool:
	expected = setting('register_code', '').strip()
	if not expected:
		return False
	return code.strip() == expected


def consume_free_use(user_id : int) -> int:
	with closing(get_db()) as connection:
		row = connection.execute(
			'SELECT free_uses_remaining FROM users WHERE id = ? AND is_admin = 0 AND is_paid = 0',
			(user_id,)
		).fetchone()
		if not row or int(row['free_uses_remaining'] or 0) <= 0:
			return 0
		remaining = int(row['free_uses_remaining']) - 1
		connection.execute('UPDATE users SET free_uses_remaining = ? WHERE id = ?', (remaining, user_id))
		connection.commit()
		return remaining


def needs_password_hint() -> bool:
	return setting('admin_password_changed', '0') != '1'


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
	user = current_user(request)
	payload = {
		'request': request,
		'user': user,
		'trial_enabled': setting('trial_enabled') == '1',
		'membership_price_usdt': setting('membership_price_usdt', '20'),
		'need_password_hint': bool(user and user.get('is_admin') and needs_password_hint()),
		'default_admin_email': DEFAULT_ADMIN_EMAIL
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
	return render(request, 'register.html', {
		'error': '',
		'register_code_required': register_code_required(),
		'new_user_free_uses': new_user_free_uses()
	})


@app.post('/register')
def register(
	request : Request,
	email : str = Form(...),
	password : str = Form(...),
	password2 : str = Form(...),
	register_code : str = Form('')
):
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
	elif register_code_required():
		if not setting('register_code', '').strip():
			error = '注册暂未开放，请联系管理员。'
		elif not register_code.strip():
			error = '请填写注册码。'
		elif not validate_register_code(register_code):
			error = '注册码不正确。'
	if error:
		return render(request, 'register.html', {
			'error': error,
			'email': email,
			'register_code_required': register_code_required(),
			'new_user_free_uses': new_user_free_uses()
		})
	grant = new_user_free_uses()
	with closing(get_db()) as connection:
		connection.execute(
			'INSERT INTO users(email, password_hash, is_admin, is_paid, free_uses_remaining, created_at) VALUES (?, ?, 0, 0, ?, ?)',
			(email, hash_password(password), grant, utc_now())
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
	price = setting('membership_price_usdt', '20')
	with closing(get_db()) as connection:
		orders = [
			dict(row) for row in connection.execute(
				'SELECT id, amount_usdt, tx_hash, status, note, created_at, paid_at FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 10',
				(user['id'],)
			).fetchall()
		]
	return render(request, 'buy.html', {
		'wallet': wallet,
		'wallet_qr': wallet_qr_svg(wallet),
		'price': price,
		'orders': orders,
		'error': '',
		'message': '',
		'support_telegram': SUPPORT_TELEGRAM,
		'free_uses_remaining': int(user.get('free_uses_remaining') or 0)
	})


@app.post('/buy')
def buy_submit(request : Request, tx_hash : str = Form(...)):
	user = current_user(request)
	if not user:
		return RedirectResponse('/login', status_code = 303)
	if user['is_admin'] or user['is_paid']:
		return RedirectResponse('/', status_code = 303)
	wallet = setting('usdt_trc20_wallet', '').strip()
	price = setting('membership_price_usdt', '20').strip() or '20'
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
		'wallet_qr': wallet_qr_svg(wallet),
		'price': price,
		'orders': orders,
		'error': error,
		'message': message,
		'support_telegram': SUPPORT_TELEGRAM,
		'free_uses_remaining': int(user.get('free_uses_remaining') or 0)
	})


@app.get('/admin')
def admin_page(request : Request):
	user = current_user(request)
	if not user or not user['is_admin']:
		return RedirectResponse('/login', status_code = 303)
	with closing(get_db()) as connection:
		users = [ dict(row) for row in connection.execute(
			'SELECT id, email, is_admin, is_paid, free_uses_remaining, created_at FROM users ORDER BY id DESC'
		).fetchall() ]
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
	flash = str(request.session.pop('admin_flash', '') or '')
	web_git = git_status(fetch = True)
	releases_git = releases_status(fetch = True)
	return render(request, 'admin.html', {
		'users': users,
		'message': flash,
		'app_version': setting('app_version', default_version()),
		'release_notes': setting('release_notes', ''),
		'update_enabled': setting('update_enabled', '1') == '1',
		'client_update_on_startup': setting('client_update_on_startup', '1') == '1',
		'trial_enabled': setting('trial_enabled') == '1',
		'register_code_required': register_code_required(),
		'register_code': setting('register_code', ''),
		'new_user_free_uses': setting('new_user_free_uses', '3'),
		'manifest_version': manifest.get('version', ''),
		'manifest_files': len(manifest.get('files') or []),
		'usdt_trc20_wallet': setting('usdt_trc20_wallet', ''),
		'membership_price_usdt': setting('membership_price_usdt', '20'),
		'orders': pending_orders,
		'web_git': web_git,
		'web_update_log': read_log_tail(),
		'releases_git': releases_git,
		'releases_root': str(releases_dir())
	})


@app.post('/admin/releases/check')
def admin_releases_check(request : Request):
	user = current_user(request)
	if not user or not user['is_admin']:
		return RedirectResponse('/login', status_code = 303)
	result = check_releases()
	request.session['admin_flash'] = result.get('message') or result.get('reason') or '检查完成。'
	return RedirectResponse('/admin', status_code = 303)


@app.post('/admin/releases/pull')
def admin_releases_pull(request : Request):
	user = current_user(request)
	if not user or not user['is_admin']:
		return RedirectResponse('/login', status_code = 303)
	result = pull_releases()
	request.session['admin_flash'] = result.get('message') or result.get('reason') or '已拉取。'
	return RedirectResponse('/admin', status_code = 303)


@app.post('/admin/web-update/check')
def admin_web_update_check(request : Request):
	user = current_user(request)
	if not user or not user['is_admin']:
		return RedirectResponse('/login', status_code = 303)
	result = check_web_update()
	request.session['admin_flash'] = result.get('message') or result.get('reason') or '检查完成。'
	return RedirectResponse('/admin', status_code = 303)


@app.post('/admin/web-update/apply')
def admin_web_update_apply(request : Request):
	user = current_user(request)
	if not user or not user['is_admin']:
		return RedirectResponse('/login', status_code = 303)
	result = apply_web_update()
	request.session['admin_flash'] = result.get('message') or result.get('reason') or '已提交更新。'
	return RedirectResponse('/admin', status_code = 303)


@app.post('/admin/trial')
def admin_trial(request : Request, trial_enabled : Optional[str] = Form(None)):
	user = current_user(request)
	if not user or not user['is_admin']:
		return RedirectResponse('/login', status_code = 303)
	set_setting('trial_enabled', '1' if trial_enabled else '0')
	return RedirectResponse('/admin', status_code = 303)


@app.post('/admin/register')
def admin_register_settings(
	request : Request,
	register_code_required_flag : Optional[str] = Form(None),
	register_code : str = Form(''),
	new_user_free_uses : str = Form('3')
):
	user = current_user(request)
	if not user or not user['is_admin']:
		return RedirectResponse('/login', status_code = 303)
	set_setting('register_code_required', '1' if register_code_required_flag else '0')
	set_setting('register_code', register_code.strip())
	set_setting('new_user_free_uses', str(parse_free_uses(new_user_free_uses)))
	return RedirectResponse('/admin', status_code = 303)


@app.post('/admin/free_uses/{user_id}')
def admin_free_uses(request : Request, user_id : int, free_uses_remaining : str = Form(...)):
	user = current_user(request)
	if not user or not user['is_admin']:
		return RedirectResponse('/login', status_code = 303)
	count = parse_free_uses(free_uses_remaining)
	with closing(get_db()) as connection:
		connection.execute(
			'UPDATE users SET free_uses_remaining = ? WHERE id = ? AND is_admin = 0',
			(count, user_id)
		)
		connection.commit()
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
	membership_price_usdt : str = Form('20')
):
	user = current_user(request)
	if not user or not user['is_admin']:
		return RedirectResponse('/login', status_code = 303)
	set_setting('usdt_trc20_wallet', usdt_trc20_wallet.strip())
	price = membership_price_usdt.strip() or '20'
	try:
		Decimal(price)
	except Exception:
		price = '20'
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


@app.get('/admin/password')
def admin_password_page(request : Request):
	user = current_user(request)
	if not user or not user['is_admin']:
		return RedirectResponse('/login', status_code = 303)
	return render(request, 'admin_password.html', {'error': '', 'message': ''})


@app.post('/admin/password')
def admin_password_save(
	request : Request,
	old_password : str = Form(...),
	new_password : str = Form(...),
	new_password2 : str = Form(...)
):
	user = current_user(request)
	if not user or not user['is_admin']:
		return RedirectResponse('/login', status_code = 303)
	error = ''
	message = ''
	if not verify_password(old_password, user['password_hash']):
		error = '当前密码不对。'
	elif len(new_password) < 8:
		error = '新密码至少 8 位。'
	elif new_password != new_password2:
		error = '两次新密码不一致。'
	elif new_password == DEFAULT_ADMIN_PASSWORD:
		error = '请不要继续使用默认密码。'
	if error:
		return render(request, 'admin_password.html', {'error': error, 'message': ''})
	with closing(get_db()) as connection:
		connection.execute(
			'UPDATE users SET password_hash = ? WHERE id = ?',
			(hash_password(new_password), user['id'])
		)
		connection.commit()
	set_setting('admin_password_changed', '1')
	message = '密码已更新。请牢记新密码。'
	return render(request, 'admin_password.html', {'error': '', 'message': message})


@app.post('/admin/release')
def admin_release(
	request : Request,
	app_version : str = Form(...),
	release_notes : str = Form(''),
	update_enabled : Optional[str] = Form(None),
	client_update_on_startup : Optional[str] = Form(None),
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
	set_setting('client_update_on_startup', '1' if client_update_on_startup else '0')
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
		setting('update_enabled', '1') == '1',
		setting('client_update_on_startup', '1') == '1'
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
	free_remaining = int(user.get('free_uses_remaining') or 0)
	if free_remaining <= 0:
		return JSONResponse({
			'ok': False,
			'reason': '免费次数已用完。请在网站购买会员后登录，或联系管理员。'
		}, status_code = 403)
	remaining = consume_free_use(int(user['id']))
	return {
		'ok': True,
		'paid': False,
		'email': user['email'],
		'free_remaining': remaining,
		'free_uses_left': remaining
	}


@app.post('/api/trial/start')
def api_trial_start():
	if setting('trial_enabled') != '1':
		return JSONResponse({'ok': False, 'reason': '试用已暂停。'}, status_code = 403)
	return {'ok': True, 'trial': True}
