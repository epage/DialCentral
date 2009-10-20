#!/usr/bin/env python

import sys


sys.path.insert(0,"/usr/lib/dialcentral/")


import alarm_notify


def notify_on_change():
	notifyUser = alarm_notify.is_changed()

	if notifyUser:
		import subprocess
		import led_handler
		led = led_handler.LedHandler()
		led.on()
		soundOn = subprocess.call("/usr/bin/dbus-send --dest=com.nokia.osso_media_server --print-reply /com/nokia/osso_media_server com.nokia.osso_media_server.music.play_media string:file:///usr/lib/gv-notifier/alert.mp3",shell=True)


if __name__ == "__main__":
	notify_on_change()
