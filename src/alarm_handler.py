#!/usr/bin/env python

import os
import time
import datetime
import ConfigParser

import dbus


_FREMANTLE_ALARM = "Fremantle"
_DIABLO_ALARM = "Diablo"
_NO_ALARM = "None"


try:
	import alarm
	ALARM_TYPE = _FREMANTLE_ALARM
except (ImportError, OSError):
	try:
		import osso.alarmd as alarmd
		ALARM_TYPE = _DIABLO_ALARM
	except (ImportError, OSError):
		ALARM_TYPE = _NO_ALARM


def _get_start_time(recurrence):
	now = datetime.datetime.now()
	startTimeMinute = now.minute + max(recurrence, 5) # being safe
	startTimeHour = now.hour + int(startTimeMinute / 60)
	startTimeMinute = startTimeMinute % 59
	now.replace(minute=startTimeMinute)
	timestamp = int(time.mktime(now.timetuple()))
	return timestamp


def _create_recurrence_mask(recurrence, base):
	"""
	>>> bin(_create_recurrence_mask(60, 60))
	'0b1'
	>>> bin(_create_recurrence_mask(30, 60))
	'0b1000000000000000000000000000001'
	>>> bin(_create_recurrence_mask(2, 60))
	'0b10101010101010101010101010101010101010101010101010101010101'
	>>> bin(_create_recurrence_mask(1, 60))
	'0b111111111111111111111111111111111111111111111111111111111111'
	"""
	mask = 0
	for i in xrange(base / recurrence):
		mask |= 1 << (recurrence * i)
	return mask


def _unpack_minutes(recurrence):
	"""
	>>> _unpack_minutes(0)
	(0, 0, 0)
	>>> _unpack_minutes(1)
	(0, 0, 1)
	>>> _unpack_minutes(59)
	(0, 0, 59)
	>>> _unpack_minutes(60)
	(0, 1, 0)
	>>> _unpack_minutes(129)
	(0, 2, 9)
	>>> _unpack_minutes(5 * 60 * 24 + 3 * 60 + 2)
	(5, 3, 2)
	>>> _unpack_minutes(12 * 60 * 24 + 3 * 60 + 2)
	(5, 3, 2)
	"""
	minutesInAnHour = 60
	minutesInDay = 24 * minutesInAnHour
	minutesInAWeek = minutesInDay * 7

	days = recurrence / minutesInDay
	daysOfWeek = days % 7
	recurrence -= days * minutesInDay
	hours = recurrence / minutesInAnHour
	recurrence -= hours * minutesInAnHour
	mins = recurrence % minutesInAnHour
	recurrence -= mins
	assert recurrence == 0, "Recurrence %d" % recurrence
	return daysOfWeek, hours, mins


class _FremantleAlarmHandler(object):

	_INVALID_COOKIE = -1
	_REPEAT_FOREVER = -1
	_TITLE = "Dialcentral Notifications"
	_LAUNCHER = os.path.abspath(os.path.join(os.path.dirname(__file__), "alarm_notify.py"))

	def __init__(self):
		self._recurrence = 5

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

	def _set_alarm(self, recurrenceMins):
		assert 1 <= recurrenceMins, "Notifications set to occur too frequently: %d" % recurrenceMins
		alarmTime = _get_start_time(recurrenceMins)

		event = alarm.Event()
		event.appid = self._TITLE
		event.alarm_time = alarmTime
		event.recurrences_left = self._REPEAT_FOREVER

		action = event.add_actions(1)[0]
		action.flags |= alarm.ACTION_TYPE_EXEC | alarm.ACTION_WHEN_TRIGGERED
		action.command = self._launcher

		recurrence = event.add_recurrences(1)[0]
		recurrence.mask_min |= _create_recurrence_mask(recurrenceMins, 60)
		recurrence.mask_hour |= alarm.RECUR_HOUR_DONTCARE
		recurrence.mask_mday |= alarm.RECUR_MDAY_DONTCARE
		recurrence.mask_wday |= alarm.RECUR_WDAY_DONTCARE
		recurrence.mask_mon |= alarm.RECUR_MON_DONTCARE
		recurrence.special |= alarm.RECUR_SPECIAL_NONE

		assert event.is_sane()
		self._alarmCookie = alarm.add_event(event)

	def _clear_alarm(self):
		if self._alarmCookie == self._INVALID_COOKIE:
			return
		alarm.delete_event(self._alarmCookie)
		self._alarmCookie = self._INVALID_COOKIE


class _DiabloAlarmHandler(object):

	_INVALID_COOKIE = -1
	_TITLE = "Dialcentral Notifications"
	_LAUNCHER = os.path.abspath(os.path.join(os.path.dirname(__file__), "alarm_notify.py"))
	_REPEAT_FOREVER = -1

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

	def _set_alarm(self, recurrence):
		assert 1 <= recurrence, "Notifications set to occur too frequently: %d" % recurrence
		alarmTime = _get_start_time(recurrence)

		#Setup the alarm arguments so that they can be passed to the D-Bus add_event method
		_DEFAULT_FLAGS = (
			alarmd.ALARM_EVENT_NO_DIALOG |
			alarmd.ALARM_EVENT_NO_SNOOZE |
			alarmd.ALARM_EVENT_CONNECTED
		)
		action = []
		action.extend(['flags', _DEFAULT_FLAGS])
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


class _NoneAlarmHandler(object):

	def __init__(self):
		self._alarmCookie = 0

	def load_settings(self, config, sectionName):
		pass

	def save_settings(self, config, sectionName):
		pass

	def apply_settings(self, enabled, recurrence):
		pass

	@property
	def recurrence(self):
		return 0

	@property
	def isEnabled(self):
		return False


AlarmHandler = {
	_FREMANTLE_ALARM: _FremantleAlarmHandler,
	_DIABLO_ALARM: _DiabloAlarmHandler,
	_NO_ALARM: _NoneAlarmHandler,
}[ALARM_TYPE]


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
