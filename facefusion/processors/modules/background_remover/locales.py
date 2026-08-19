from facefusion.types import Locales

LOCALES : Locales =\
{
	'en':
	{
		'help':
		{
			'model': 'choose the model responsible for removing the background',
			'fill_color': 'apply red, green, blue and alpha values to the background',
			'despill_color': 'remove red, green, blue and alpha values from the foreground'
		},
		'uis':
		{
			'model_dropdown': 'BACKGROUND REMOVER MODEL',
			'fill_color_red_number': 'FILL COLOR RED',
			'fill_color_green_number': 'FILL COLOR GREEN',
			'fill_color_blue_number': 'FILL COLOR BLUE',
			'fill_color_alpha_number': 'FILL COLOR ALPHA',
			'despill_color_red_number': 'DESPILL COLOR RED',
			'despill_color_green_number': 'DESPILL COLOR GREEN',
			'despill_color_blue_number': 'DESPILL COLOR BLUE',
			'despill_color_alpha_number': 'DESPILL COLOR ALPHA'
		}
	},
	'zh':
	{
		'help':
		{
			'model': '选择抠背景模型',
			'fill_color': '设置背景的红、绿、蓝和透明度',
			'despill_color': '从前景去除红、绿、蓝和透明度溢出'
		},
		'uis':
		{
			'model_dropdown': '抠背景模型',
			'fill_color_red_number': '填充红色',
			'fill_color_green_number': '填充绿色',
			'fill_color_blue_number': '填充蓝色',
			'fill_color_alpha_number': '填充透明度',
			'despill_color_red_number': '去溢出红色',
			'despill_color_green_number': '去溢出绿色',
			'despill_color_blue_number': '去溢出蓝色',
			'despill_color_alpha_number': '去溢出透明度'
		}
	}
}
