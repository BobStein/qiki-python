"""Update version.py, a docstring-only module with a timestamped version-code."""

import datetime

VERSION_BASE = '0.0.1'
VERSION_PY = 'qiki/version.py'
yyyy_mmdd_hhmm_ss = datetime.datetime.utcnow().strftime('%Y.%m%d.%H%M.%S')
# EXAMPLE:  UTC timestamp "2019.0524.1959.39"

with open(VERSION_PY, 'w') as version_py:
    version_py.write('"""')
    version_py.write(VERSION_BASE)
    version_py.write('.')
    version_py.write(yyyy_mmdd_hhmm_ss)
    version_py.write('"""')
    # EXAMPLE:  """0.0.1.2019.0524.1959.39"""
