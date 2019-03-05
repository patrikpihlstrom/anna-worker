#!/usr/bin/python

import os
import random
import string
import unittest

if 'ANNA_SECRET' not in os.environ:
	os.environ['ANNA_SECRET'] = ''.join(random.choice(string.ascii_lowercase + string.digits) for n in range(16))

loader = unittest.TestLoader()
suite = loader.discover('tests/unit')
print('found ' + str(suite.countTestCases()) + ' test cases')
unittest.TextTestRunner().run(suite)
