#!/usr/bin/python

import os
import sys
import logging


sys.path.insert(0,"/usr/lib/dialcentral/")


import constants
import dc_glade


try:
	os.makedirs(constants._data_path_)
except OSError, e:
	if e.errno != 17:
		raise

userLogPath = "%s/dialcentral.log" % constants._data_path_
logging.basicConfig(level=logging.DEBUG, filename=userLogPath)
logging.info("Dialcentral %s-%s" % (constants.__version__, constants.__build__))

try:
	dc_glade.run_dialpad()
finally:
	logging.shutdown()
