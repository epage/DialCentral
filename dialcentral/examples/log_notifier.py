#!/usr/bin/env python

from __future__ import with_statement

import datetime
import ConfigParser

from dialcentral import constants
from dialcentral.util import linux as linux_utils
from dialcentral import alarm_notify


def notify_on_change():
	notifierLogPath = linux_utils.get_resource_path("cache", constants.__app_name__, "notifier.log")
	settingsPath = linux_utils.get_resource_path("config", constants.__app_name__, "settings.ini")
	with open(notifierLogPath, "a") as file:
		file.write("Notification: %r\n" % (datetime.datetime.now(), ))

		config = ConfigParser.SafeConfigParser()
		config.read(settingsPath)
		backend = alarm_notify.create_backend(config)
		notifyUser = alarm_notify.is_changed(config, backend)

		if notifyUser:
			file.write("\tChange occurred\n")


if __name__ == "__main__":
	notify_on_change()
