#!/usr/bin/env python

import dbus


class LedHandler(object):

	def __init__(self):
		self._bus = dbus.SystemBus()
		self._rawMceRequest = self._bus.get_object("com.nokia.mce", "/com/nokia/mce/request")
		self._mceRequest = dbus.Interface(self._rawMceRequest, dbus_interface="com.nokia.mce.request")

		self._ledPattern = "PatternCommunicationChat"

	def on(self):
		self._mceRequest.req_led_pattern_activate(self._ledPattern)

	def off(self):
		self._mceRequest.req_led_pattern_deactivate(self._ledPattern)


if __name__ == "__main__":
	leds = LedHandler()
	leds.off()
