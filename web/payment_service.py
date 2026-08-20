#!/usr/bin/env python3
"""TRC20 USDT 收款校验（TronGrid）。"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from decimal import Decimal
from typing import Any, Optional

USDT_TRC20_CONTRACT = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'
TX_HASH_RE = re.compile(r'^[0-9a-fA-F]{64}$')


def trongrid_headers() -> dict[str, str]:
	key = os.environ.get('TRONGRID_API_KEY', '').strip()
	if key:
		return {'TRON-PRO-API-KEY': key}
	return {}


def fetch_json(url : str) -> tuple[int, Any]:
	request = urllib.request.Request(url, headers = trongrid_headers(), method = 'GET')
	try:
		with urllib.request.urlopen(request, timeout = 25) as response:
			return response.status, json.loads(response.read().decode('utf-8'))
	except urllib.error.HTTPError as error:
		try:
			body = json.loads(error.read().decode('utf-8'))
		except Exception:
			body = {'ok': False}
		return error.code, body
	except Exception:
		return 0, None


def normalize_tx_hash(value : str) -> str:
	value = (value or '').strip()
	if value.lower().startswith('0x'):
		value = value[2:]
	return value.lower()


def usdt_amount(raw_value : str, decimals : int = 6) -> Decimal:
	return Decimal(str(raw_value or '0')) / (Decimal(10) ** decimals)


def verify_trc20_usdt(tx_hash : str, wallet : str, min_amount : Decimal) -> tuple[bool, str]:
	tx_hash = normalize_tx_hash(tx_hash)
	wallet = (wallet or '').strip()
	if not TX_HASH_RE.match(tx_hash):
		return False, '交易哈希格式不对（应为 64 位十六进制）。'
	if not wallet:
		return False, '尚未配置收款地址。'

	code, payload = fetch_json(f'https://api.trongrid.io/v1/transactions/{tx_hash}/events')
	if code != 200 or not payload:
		return False, '暂时无法查询链上记录，请稍后重试或联系管理员人工开通。'

	events = payload.get('data') if isinstance(payload, dict) else None
	if not events:
		code, payload = fetch_json(
			f'https://api.trongrid.io/v1/accounts/{wallet}/transactions/trc20'
			f'?only_to=true&limit=80&contract_address={USDT_TRC20_CONTRACT}'
		)
		if code != 200 or not isinstance(payload, dict):
			return False, '链上查询失败，请稍后重试。'
		for item in payload.get('data') or []:
			if normalize_tx_hash(str(item.get('transaction_id') or '')) != tx_hash:
				continue
			if str(item.get('to') or '').strip() != wallet:
				continue
			amount = usdt_amount(str(item.get('value') or '0'))
			if amount + Decimal('0.000001') >= min_amount:
				return True, '已确认 USDT 到账。'
		return False, '未找到符合条件的 USDT 转入（地址、金额或哈希不匹配）。'

	for event in events:
		if str(event.get('event_name') or '') != 'Transfer':
			continue
		if str(event.get('contract_address') or '') != USDT_TRC20_CONTRACT:
			continue
		result = event.get('result') or {}
		if str(result.get('to') or '').strip() != wallet:
			continue
		amount = usdt_amount(str(result.get('value') or '0'))
		if amount + Decimal('0.000001') >= min_amount:
			return True, '已确认 USDT 到账。'
	return False, '未找到符合条件的 USDT 转入（地址、金额或哈希不匹配）。'
