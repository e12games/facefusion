from facefusion.types import Locales

LOCALES : Locales =\
{
	'en':
	{
		'help':
		{
			'model': 'choose the model responsible for colorizing the frame',
			'size': 'specify the frame size provided to the frame colorizer',
			'blend': 'blend the colorized into the previous frame'
		},
		'uis':
		{
			'blend_slider': 'FRAME COLORIZER BLEND',
			'model_dropdown': 'FRAME COLORIZER MODEL',
			'size_dropdown': 'FRAME COLORIZER SIZE'
		}
	},
	'zh':
	{
		'help':
		{
			'model': '选择画面上色模型',
			'size': '指定送入上色模型的画面尺寸',
			'blend': '将上色结果与上一帧混合'
		},
		'uis':
		{
			'blend_slider': '画面上色混合',
			'model_dropdown': '画面上色模型',
			'size_dropdown': '画面上色尺寸'
		}
	}
}
