from facefusion import translator
from facefusion.locales import LOCALES


def test_load() -> None:
	translator.load(LOCALES, __name__)

	assert __name__ in translator.LOCALE_POOL_SET


def test_get() -> None:
	translator.set('en')
	assert translator.get('processing_stopped') == 'processing stopped'
	assert translator.get('help.run') == 'run the program'
	assert translator.get('invalid') is None


def test_get_zh() -> None:
	translator.set('zh')
	assert translator.get('processing_stopped') == '处理已停止'
	assert translator.get('uis.start_button') == '开始'
	assert translator.get('help.run') == '启动程序（打开网页界面）'
	translator.set('en')
