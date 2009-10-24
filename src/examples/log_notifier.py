#!/usr/bin/env python

from __future__ import with_statement

import sys
import datetime
import ConfigParser


sys.path.insert(0,"/usr/lib/dialcentral/")


import constants
import alarm_notify


def notify_on_change():
	filename = "%s/notification.log" % constants._data_path_
	with open(filename, "a") as file:
		file.write("Notification: %r\n" % (datetime.datetime.now(), ))

		config = ConfigParser.SafeConfigParser()
		config.read(constants._user_settings_)
		backend = alarm_notify.create_backend(config)
		notifyUser = alarm_notify.is_changed(config, backend)

		if notifyUser:
			file.write("\tChange occurred\n")


if __name__ == "__main__":
	notify_on_change()
