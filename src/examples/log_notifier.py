#!/usr/bin/env python

from __future__ import with_statement

import sys
import datetime


sys.path.insert(0,"/usr/lib/dialcentral/")


import constants
import alarm_notify


def notify_on_change():
	filename = "%s/notification.log" % constants._data_path_
	with open(filename, "a") as file:
		file.write("Notification: %r\n" % (datetime.datetime.now(), ))
		notifyUser = alarm_notify.is_changed()
		if notifyUser:
			file.write("\tChange occurred\n")


if __name__ == "__main__":
	notify_on_change()
