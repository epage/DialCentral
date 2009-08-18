#!/usr/bin/env python

import os
import filecmp
import ConfigParser
import pprint

import constants
import gv_backend


def get_missed(backend):
	missedPage = backend._browser.download(backend._missedCallsURL)
	missedJson = backend._grab_json(missedPage)
	return missedJson


def get_voicemail(backend):
	voicemailPage = backend._browser.download(backend._voicemailURL)
	voicemailJson = backend._grab_json(voicemailPage)
	return voicemailJson


def get_sms(backend):
	smsPage = backend._browser.download(backend._smsURL)
	smsJson = backend._grab_json(smsPage)
	return smsJson


def remove_reltime(data):
	for messageData in data["messages"].itervalues():
		del messageData["relativeStartTime"]


def is_type_changed(backend, type, get_material):
	jsonMaterial = get_material(backend)
	unreadCount = jsonMaterial["unreadCounts"][type]

	previousSnapshotPath = os.path.join(constants._data_path_, "snapshot_%s.old.json" % type)
	currentSnapshotPath = os.path.join(constants._data_path_, "snapshot_%s.json" % type)

	try:
		os.remove(previousSnapshotPath)
	except OSError, e:
		# check if failed purely because the old file didn't exist, which is fine
		if e.errno != 2:
			raise
	try:
		os.rename(currentSnapshotPath, previousSnapshotPath)
		previousExists = True
	except OSError, e:
		# check if failed purely because the new old file didn't exist, which is fine
		if e.errno != 2:
			raise
		previousExists = False

	remove_reltime(jsonMaterial)
	textMaterial = pprint.pformat(jsonMaterial)
	currentSnapshot = file(currentSnapshotPath, "w")
	try:
		currentSnapshot.write(textMaterial)
	finally:
		currentSnapshot.close()

	if unreadCount == 0 or not previousExists:
		return False

	seemEqual = filecmp.cmp(previousSnapshotPath, currentSnapshotPath)
	return not seemEqual


def is_changed():
	gvCookiePath = os.path.join(constants._data_path_, "gv_cookies.txt")
	backend = gv_backend.GVDialer(gvCookiePath)

	loggedIn = False

	if not loggedIn:
		loggedIn = backend.is_authed()

	config = ConfigParser.SafeConfigParser()
	config.read(constants._user_settings_)
	if not loggedIn:
		import base64
		try:
			blobs = (
				config.get(constants.__pretty_app_name__, "bin_blob_%i" % i)
				for i in xrange(2)
			)
			creds = (
				base64.b64decode(blob)
				for blob in blobs
			)
			username, password = tuple(creds)
			loggedIn = backend.login(username, password)
		except ConfigParser.NoOptionError, e:
			pass
		except ConfigParser.NoSectionError, e:
			pass

	try:
		notifyOnMissed = config.getboolean("2 - Account Info", "notifyOnMissed")
		notifyOnVoicemail = config.getboolean("2 - Account Info", "notifyOnVoicemail")
		notifyOnSms = config.getboolean("2 - Account Info", "notifyOnSms")
	except ConfigParser.NoOptionError, e:
		notifyOnMissed = False
		notifyOnVoicemail = False
		notifyOnSms = False
	except ConfigParser.NoSectionError, e:
		notifyOnMissed = False
		notifyOnVoicemail = False
		notifyOnSms = False

	assert loggedIn
	notifySources = []
	if notifyOnMissed:
		notifySources.append(("missed", get_missed))
	if notifyOnVoicemail:
		notifySources.append(("voicemail", get_voicemail))
	if notifyOnSms:
		notifySources.append(("sms", get_sms))

	notifyUser = False
	for type, get_material in notifySources:
		if is_type_changed(backend, type, get_material):
			notifyUser = True
	return notifyUser


def notify_on_change():
	notifyUser = is_changed()

	if notifyUser:
		import led_handler
		led = led_handler.LedHandler()
		led.on()


if __name__ == "__main__":
	notify_on_change()
