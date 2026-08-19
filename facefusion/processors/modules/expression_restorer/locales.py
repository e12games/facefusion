from facefusion.types import Locales

LOCALES : Locales =\
{
	'en':
	{
		'help':
		{
			'model': 'choose the model responsible for restoring the expression',
			'factor': 'restore factor of expression from the target face',
			'areas': 'choose the items used for the expression areas (choices: {choices})'
		},
		'uis':
		{
			'model_dropdown': 'EXPRESSION RESTORER MODEL',
			'factor_slider': 'EXPRESSION RESTORER FACTOR',
			'areas_checkbox_group': 'EXPRESSION RESTORER AREAS'
		}
	},
	'zh':
	{
		'help':
		{
			'model': '选择表情还原模型',
			'factor': '从目标脸还原表情的程度',
			'areas': '选择表情还原区域（可选：{choices}）'
		},
		'uis':
		{
			'model_dropdown': '表情还原模型',
			'factor_slider': '表情还原强度',
			'areas_checkbox_group': '表情还原区域'
		}
	}
}
