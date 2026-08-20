import random
from typing import Optional

import gradio

from facefusion import metadata, translator

METADATA_BUTTON : Optional[gradio.Button] = None
ACTION_BUTTON : Optional[gradio.Button] = None

SITE_URL = 'https://facefusion.iqiyia.cyou/'


def render() -> None:
	global METADATA_BUTTON
	global ACTION_BUTTON

	action = random.choice(
	[
		{
			'translator': translator.get('about.fund'),
			'url': SITE_URL
		},
		{
			'translator': translator.get('about.subscribe'),
			'url': SITE_URL
		},
		{
			'translator': translator.get('about.join'),
			'url': SITE_URL
		}
	])

	METADATA_BUTTON = gradio.Button(
		value = metadata.get('name') + ' ' + metadata.get('version'),
		variant = 'primary',
		link = metadata.get('url') or SITE_URL
	)
	ACTION_BUTTON = gradio.Button(
		value = action.get('translator'),
		link = action.get('url'),
		size = 'sm'
	)
