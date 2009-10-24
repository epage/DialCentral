#!/usr/bin/env python

import sys
import ConfigParser


sys.path.insert(0,"/usr/lib/dialcentral/")


import constants
import alarm_notify


def notify_on_change():
	config = ConfigParser.SafeConfigParser()
	config.read(constants._user_settings_)
	backend = alarm_notify.create_backend(config)
	notifyUser = alarm_notify.is_changed(config, backend)

	if notifyUser:
		import subprocess
		import led_handler
		led = led_handler.LedHandler()
		led.on()
		soundOn = subprocess.call("/usr/bin/dbus-send --dest=com.nokia.osso_media_server --print-reply /com/nokia/osso_media_server com.nokia.osso_media_server.music.play_media string:file:///usr/lib/gv-notifier/alert.mp3",shell=True)


if __name__ == "__main__":
	notify_on_change()
