import os
import shutil
import signal
import subprocess
import sys
from argparse import ArgumentParser, HelpFormatter
from configparser import ConfigParser
from functools import partial
from types import FrameType

from facefusion import metadata
from facefusion.common_helper import is_linux, is_windows

INSTALLER_LOCALES =\
{
	'en':
	{
		'install_dependency': 'install the {dependency} package',
		'force_reinstall': 'force reinstall of packages',
		'skip_conda': 'skip the conda environment check',
		'conda_not_activated': 'conda is not activated'
	},
	'zh':
	{
		'install_dependency': '安装 {dependency} 依赖包',
		'force_reinstall': '强制重新安装依赖包',
		'skip_conda': '跳过 conda 环境检查',
		'conda_not_activated': '尚未激活 conda 环境'
	}
}


def detect_installer_language() -> str:
	environment_language = (os.environ.get('FACEFUSION_LANGUAGE') or '').strip().lower()

	if environment_language in [ 'zh', 'zh-cn', 'zh_cn', 'chinese', 'cn' ]:
		return 'zh'
	if environment_language in [ 'en', 'english' ]:
		return 'en'

	config_parser = ConfigParser()
	config_parser.read('facefusion.ini', encoding = 'utf-8')

	if config_parser.has_option('misc', 'language'):
		config_language = config_parser.get('misc', 'language').strip().lower()

		if config_language in [ 'zh', 'zh-cn', 'zh_cn', 'chinese', 'cn' ]:
			return 'zh'

	return 'en'


def get_installer_text(notation : str) -> str:
	language_locales = INSTALLER_LOCALES.get(detect_installer_language(), INSTALLER_LOCALES['en'])

	return language_locales.get(notation, INSTALLER_LOCALES['en'].get(notation, ''))


ONNXRUNTIME_SET =\
{
	'default': ('onnxruntime', '1.28.0')
}
if is_windows() or is_linux():
	ONNXRUNTIME_SET['cuda@12'] = ('onnxruntime-gpu', '1.24.4')
	ONNXRUNTIME_SET['cuda@13'] = ('onnxruntime-gpu', '1.28.0')
	ONNXRUNTIME_SET['openvino'] = ('onnxruntime-openvino', '1.24.1')
if is_windows():
	ONNXRUNTIME_SET['directml'] = ('onnxruntime-directml', '1.24.4')
	ONNXRUNTIME_SET['qnn'] = ('onnxruntime-qnn', '2.4.0')
if is_linux():
	ONNXRUNTIME_SET['migraphx'] = ('onnxruntime-migraphx', '1.27.1')
	ONNXRUNTIME_SET['rocm'] = ('onnxruntime-rocm', '1.22.2.post3')


def cli() -> None:
	signal.signal(signal.SIGINT, signal_exit)
	program = ArgumentParser(formatter_class = partial(HelpFormatter, max_help_position = 50))
	program.add_argument('onnxruntime', help = get_installer_text('install_dependency').format(dependency = 'onnxruntime'), choices = ONNXRUNTIME_SET.keys())
	program.add_argument('--force-reinstall', help = get_installer_text('force_reinstall'), action = 'store_true')
	program.add_argument('--skip-conda', help = get_installer_text('skip_conda'), action = 'store_true')
	program.add_argument('-v', '--version', version = metadata.get('name') + ' ' + metadata.get('version'), action = 'version')
	run(program)


def signal_exit(signum : int, frame : FrameType) -> None:
	sys.exit(0)


def run(program : ArgumentParser) -> None:
	args = program.parse_args()
	has_conda = 'CONDA_PREFIX' in os.environ

	if not args.skip_conda and not has_conda:
		sys.stdout.write(get_installer_text('conda_not_activated') + os.linesep)
		sys.exit(1)

	for onnxruntime_package, _ in ONNXRUNTIME_SET.values():
		subprocess.call([ shutil.which('pip'), 'uninstall', onnxruntime_package, '-y', '-q' ], stderr = subprocess.DEVNULL)

	commands = [ shutil.which('pip'), 'install' ]

	if args.force_reinstall:
		commands.append('--force-reinstall')

	with open('requirements.txt') as file:

		for line in file.readlines():
			__line__ = line.strip()

			if not __line__.startswith('onnxruntime'):
				commands.append(__line__)

	onnxruntime_name, onnxruntime_version = ONNXRUNTIME_SET.get(args.onnxruntime)
	commands.append(onnxruntime_name + '==' + onnxruntime_version)
	subprocess.call(commands)
