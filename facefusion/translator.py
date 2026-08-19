import importlib
import os
import sys
from configparser import ConfigParser
from typing import Any, Dict, Optional

from facefusion.types import Language, LocalePoolSet, Locales

LOCALE_POOL_SET : LocalePoolSet = {}
CURRENT_LANGUAGE : Language = 'en'
LANGUAGE_ALIASES =\
{
	'en': 'en',
	'english': 'en',
	'zh': 'zh',
	'zh-cn': 'zh',
	'zh_cn': 'zh',
	'zh-hans': 'zh',
	'chinese': 'zh',
	'cn': 'zh'
}


def __autoload__(module_name : str) -> None:
	try:
		__locales__ = importlib.import_module(module_name + '.locales')
		load(__locales__.LOCALES, module_name)
	except ImportError:
		pass


def load(__locales__ : Locales, module_name : str) -> None:
	LOCALE_POOL_SET[module_name] = __locales__


def set(language : Optional[str]) -> None:
	global CURRENT_LANGUAGE

	normalized_language = LANGUAGE_ALIASES.get((language or '').strip().lower())

	if normalized_language:
		CURRENT_LANGUAGE = normalized_language #type:ignore[assignment]


def init() -> None:
	set(_detect_language())


def _detect_language() -> str:
	if '--language' in sys.argv:
		language_index = sys.argv.index('--language') + 1

		if language_index < len(sys.argv):
			return sys.argv[language_index]

	environment_language = os.environ.get('FACEFUSION_LANGUAGE')

	if environment_language:
		return environment_language

	config_parser = ConfigParser()
	config_parser.read('facefusion.ini', encoding = 'utf-8')

	if config_parser.has_option('misc', 'language'):
		config_language = config_parser.get('misc', 'language').strip()

		if config_language:
			return config_language

	return 'en'


def get(notation : str, module_name : str = 'facefusion') -> Optional[str]:
	if module_name not in LOCALE_POOL_SET:
		__autoload__(module_name)

	locales = LOCALE_POOL_SET.get(module_name) or {}
	result = _lookup(locales.get(CURRENT_LANGUAGE) or {}, notation)

	if result is None and CURRENT_LANGUAGE != 'en':
		result = _lookup(locales.get('en') or {}, notation)

	return result


def _lookup(locale_tree : Dict[str, Any], notation : str) -> Optional[str]:
	current : Any = locale_tree

	for fragment in notation.split('.'):
		if not isinstance(current, dict) or fragment not in current:
			return None

		current = current.get(fragment)

		if isinstance(current, str):
			return current

	return None
