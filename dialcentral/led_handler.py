#!/usr/bin/env python

import dbus


class _NokiaLedHandler(object):

	def __init__(self):
		self._bus = dbus.SystemBus()
		self._rawMceRequest = self._bus.get_object("com.nokia.mce", "/com/nokia/mce/request")
		self._mceRequest = dbus.Interface(self._rawMceRequest, dbus_interface="com.nokia.mce.request")

		self._ledPattern = "PatternCommunicationChat"

	def on(self):
		self._mceRequest.req_led_pattern_activate(self._ledPattern)

	def off(self):
		self._mceRequest.req_led_pattern_deactivate(self._ledPattern)


class _NoLedHandler(object):

	def __init__(self):
		pass

	def on(self):
		pass

	def off(self):
		pass


class LedHandler(object):

	def __init__(self):
		self._actual = None
		self._isReal = False

	def on(self):
		self._lazy_init()
		self._actual.on()

	def off(self):
		self._lazy_init()
		self._actual.off()

	@property
	def isReal(self):
		self._lazy_init()
		self._isReal

	def _lazy_init(self):
		if self._actual is not None:
			return
		try:
			self._actual = _NokiaLedHandler()
			self._isReal = True
		except dbus.DBusException:
			self._actual = _NoLedHandler()
			self._isReal = False


if __name__ == "__main__":
	leds = _NokiaLedHandler()
	leds.off()
