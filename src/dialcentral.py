#!/usr/bin/python

import os
import sys
import logging


_moduleLogger = logging.getLogger("dialcentral")
sys.path.insert(0,"/opt/dialcentral/lib")


import constants
import dc_glade


try:
	os.makedirs(constants._data_path_)
except OSError, e:
	if e.errno != 17:
		raise

logging.basicConfig(level=logging.DEBUG, filename=constants._user_logpath_)
_moduleLogger.info("Dialcentral %s-%s" % (constants.__version__, constants.__build__))
_moduleLogger.info("OS: %s" % (os.uname()[0], ))
_moduleLogger.info("Kernel: %s (%s) for %s" % os.uname()[2:])
_moduleLogger.info("Hostname: %s" % os.uname()[1])

try:
	dc_glade.run_dialpad()
finally:
	logging.shutdown()
