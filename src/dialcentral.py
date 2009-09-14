#!/usr/bin/python

import sys
import logging


sys.path.insert(0,"/usr/lib/dialcentral/")


import constants
import dc_glade


userLogPath = "%s/dialcentral.log" % constants._data_path_
logging.basicConfig(level=logging.DEBUG, filename=userLogPath)
try:
	dc_glade.run_dialpad()
finally:
	logging.shutdown()
