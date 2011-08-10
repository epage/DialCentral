#!/usr/bin/env python

import os
import sys
import ConfigParser
import logging


sys.path.insert(0,"/usr/lib/dialcentral/")


import constants
import alarm_notify


def notify_on_change():
	config = ConfigParser.SafeConfigParser()
	config.read(constants._user_settings_)
	backend = alarm_notify.create_backend(config)
	notifyUser = alarm_notify.is_changed(config, backend)

	config = ConfigParser.SafeConfigParser()
	config.read(constants._custom_notifier_settings_)
	soundFile = config.get("Sound Notifier", "soundfile")
	soundFile = "/usr/lib/gv-notifier/alert.mp3"

	if notifyUser:
		import subprocess
		import led_handler
		logging.info("Changed, playing %s" % soundFile)
		led = led_handler.LedHandler()
		led.on()
		soundOn = subprocess.call("/usr/bin/dbus-send --dest=com.nokia.osso_media_server --print-reply /com/nokia/osso_media_server com.nokia.osso_media_server.music.play_media string:file://%s",shell=True)
	else:
		logging.info("No Change")


if __name__ == "__main__":
	logging.basicConfig(level=logging.WARNING, filename=constants._notifier_logpath_)
	logging.info("Sound Notifier %s-%s" % (constants.__version__, constants.__build__))
	logging.info("OS: %s" % (os.uname()[0], ))
	logging.info("Kernel: %s (%s) for %s" % os.uname()[2:])
	logging.info("Hostname: %s" % os.uname()[1])
	try:
		notify_on_change()
	except:
		logging.exception("Error")
		raise
