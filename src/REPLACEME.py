#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright (C) 2007 Christoph Würstle
This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License version 2 as
published by the Free Software Foundation.
"""


import os
import sys
import logging


_moduleLogger = logging.getLogger(__name__)
sys.path.append("/opt/REPLACEME/lib")


import constants
import REPLACEME_gtk


if __name__ == "__main__":
	try:
		os.makedirs(constants._data_path_)
	except OSError, e:
		if e.errno != 17:
			raise

	try:
		os.makedirs(constants._cache_path_)
	except OSError, e:
		if e.errno != 17:
			raise

	logFormat = '(%(asctime)s) %(levelname)-5s %(threadName)s.%(name)s: %(message)s'
	logging.basicConfig(level=logging.DEBUG, filename=constants._user_logpath_, format=logFormat)
	_moduleLogger.info("%s %s-%s" % (constants.__app_name__, constants.__version__, constants.__build__))
	_moduleLogger.info("OS: %s" % (os.uname()[0], ))
	_moduleLogger.info("Kernel: %s (%s) for %s" % os.uname()[2:])
	_moduleLogger.info("Hostname: %s" % os.uname()[1])

	REPLACEME_gtk.run()
