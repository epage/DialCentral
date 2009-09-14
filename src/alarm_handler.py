#!/usr/bin/env python

import os
import time
import datetime
import ConfigParser

import dbus
import osso.alarmd as alarmd


class AlarmHandler(object):

	_INVALID_COOKIE = -1
	_TITLE = "Dialcentral Notifications"
	_LAUNCHER = os.path.abspath(os.path.join(os.path.dirname(__file__), "alarm_notify.py"))
	_REPEAT_FOREVER = -1
	_DEFAULT_FLAGS = (
		alarmd.ALARM_EVENT_NO_DIALOG |
		alarmd.ALARM_EVENT_NO_SNOOZE |
		alarmd.ALARM_EVENT_CONNECTED
	)

	def __init__(self):
		self._recurrence = 5

		bus = dbus.SystemBus()
		self._alarmdDBus = bus.get_object("com.nokia.alarmd", "/com/nokia/alarmd");
		self._alarmCookie = self._INVALID_COOKIE
		self._launcher = self._LAUNCHER

	def load_settings(self, config, sectionName):
		try:
			self._recurrence = config.getint(sectionName, "recurrence")
			self._alarmCookie = config.getint(sectionName, "alarmCookie")
			launcher = config.get(sectionName, "notifier")
			if launcher:
				self._launcher = launcher
		except ConfigParser.NoOptionError:
			pass

	def save_settings(self, config, sectionName):
		config.set(sectionName, "recurrence", str(self._recurrence))
		config.set(sectionName, "alarmCookie", str(self._alarmCookie))
		launcher = self._launcher if self._launcher != self._LAUNCHER else ""
		config.set(sectionName, "notifier", launcher)

	def apply_settings(self, enabled, recurrence):
		if recurrence != self._recurrence or enabled != self.isEnabled:
			if self.isEnabled:
				self._clear_alarm()
			if enabled:
				self._set_alarm(recurrence)
		self._recurrence = int(recurrence)

	@property
	def recurrence(self):
		return self._recurrence

	@property
	def isEnabled(self):
		return self._alarmCookie != self._INVALID_COOKIE

	def _get_start_time(self, recurrence):
		now = datetime.datetime.now()
		startTimeMinute = now.minute + max(recurrence, 5) # being safe
		startTimeHour = now.hour + int(startTimeMinute / 60)
		startTimeMinute = startTimeMinute % 59
		now.replace(minute=startTimeMinute)
		timestamp = int(time.mktime(now.timetuple()))
		return timestamp

	def _set_alarm(self, recurrence):
		assert 1 <= recurrence, "Notifications set to occur too frequently: %d" % recurrence
		alarmTime = self._get_start_time(recurrence)

		#Setup the alarm arguments so that they can be passed to the D-Bus add_event method
		action = []
		action.extend(['flags', self._DEFAULT_FLAGS])
		action.extend(['title', self._TITLE])
		action.extend(['path', self._launcher])
		action.extend([
			'arguments',
			dbus.Array(
				[alarmTime, int(27)],
				signature=dbus.Signature('v')
			)
		])  #int(27) used in place of alarm_index

		event = []
		event.extend([dbus.ObjectPath('/AlarmdEventRecurring'), dbus.UInt32(4)])
		event.extend(['action', dbus.ObjectPath('/AlarmdActionExec')])  #use AlarmdActionExec instead of AlarmdActionDbus
		event.append(dbus.UInt32(len(action) / 2))
		event.extend(action)
		event.extend(['time', dbus.Int64(alarmTime)])
		event.extend(['recurr_interval', dbus.UInt32(recurrence)])
		event.extend(['recurr_count', dbus.Int32(self._REPEAT_FOREVER)])

		self._alarmCookie = self._alarmdDBus.add_event(*event);

	def _clear_alarm(self):
		if self._alarmCookie == self._INVALID_COOKIE:
			return
		deleteResult = self._alarmdDBus.del_event(dbus.Int32(self._alarmCookie))
		self._alarmCookie = self._INVALID_COOKIE
		assert deleteResult != -1, "Deleting of alarm event failed"


def main():
	import ConfigParser
	import constants
	try:
		import optparse
	except ImportError:
		return

	parser = optparse.OptionParser()
	parser.add_option("-x", "--display", action="store_true", dest="display", help="Display data")
	parser.add_option("-e", "--enable", action="store_true", dest="enabled", help="Whether the alarm should be enabled or not", default=False)
	parser.add_option("-d", "--disable", action="store_false", dest="enabled", help="Whether the alarm should be enabled or not", default=False)
	parser.add_option("-r", "--recurrence", action="store", type="int", dest="recurrence", help="How often the alarm occurs", default=5)
	(commandOptions, commandArgs) = parser.parse_args()

	alarmHandler = AlarmHandler()
	config = ConfigParser.SafeConfigParser()
	config.read(constants._user_settings_)
	alarmHandler.load_settings(config, "alarm")

	if commandOptions.display:
		print "Alarm (%s) is %s for every %d minutes" % (
			alarmHandler._alarmCookie,
			"enabled" if alarmHandler.isEnabled else "disabled",
			alarmHandler.recurrence,
		)
	else:
		isEnabled = commandOptions.enabled
		recurrence = commandOptions.recurrence
		alarmHandler.apply_settings(isEnabled, recurrence)

		alarmHandler.save_settings(config, "alarm")
		configFile = open(constants._user_settings_, "wb")
		try:
			config.write(configFile)
		finally:
			configFile.close()


if __name__ == "__main__":
	main()
