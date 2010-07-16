#!/usr/bin/env python


import logging


def set_process_name(name):
	try: # change process name for killall
		import ctypes
		libc = ctypes.CDLL('libc.so.6')
		libc.prctl(15, name, 0, 0, 0)
	except Exception, e:
		logging.warning('Unable to set processName: %s" % e')
