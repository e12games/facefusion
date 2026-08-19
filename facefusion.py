#!/usr/bin/env python3

import os

os.environ['OMP_NUM_THREADS'] = '1'

from facefusion import conda, core, translator

if __name__ == '__main__':
	conda.setup()
	translator.init()
	core.cli()
