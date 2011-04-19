#!/usr/bin/env python

import os
import filecmp
import ConfigParser
import pprint
import logging
import logging.handlers

import constants
from backends.gvoice import gvoice


def get_missed(backend):
	missedPage = backend._browser.download(backend._XML_MISSED_URL)
	missedJson = backend._grab_json(missedPage)
	return missedJson


def get_voicemail(backend):
	voicemailPage = backend._browser.download(backend._XML_VOICEMAIL_URL)
	voicemailJson = backend._grab_json(voicemailPage)
	return voicemailJson


def get_sms(backend):
	smsPage = backend._browser.download(backend._XML_SMS_URL)
	smsJson = backend._grab_json(smsPage)
	return smsJson


def remove_reltime(data):
	for messageData in data["messages"].itervalues():
		for badPart in [
			"relTime",
			"relativeStartTime",
			"time",
			"star",
			"isArchived",
			"isRead",
			"isSpam",
			"isTrash",
			"labels",
		]:
			if badPart in messageData:
				del messageData[badPart]
	for globalBad in ["unreadCounts", "totalSize", "resultsPerPage"]:
		if globalBad in data:
			del data[globalBad]


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


def create_backend(config):
	gvCookiePath = os.path.join(constants._data_path_, "gv_cookies.txt")
	backend = gvoice.GVoiceBackend(gvCookiePath)

	loggedIn = False

	if not loggedIn:
		loggedIn = backend.refresh_account_info() is not None

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
			loggedIn = backend.login(username, password) is not None
		except ConfigParser.NoOptionError, e:
			pass
		except ConfigParser.NoSectionError, e:
			pass

	assert loggedIn
	return backend


def is_changed(config, backend):
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
	logging.debug(
		"Missed: %s, Voicemail: %s, SMS: %s" % (notifyOnMissed, notifyOnVoicemail, notifyOnSms)
	)

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
	config = ConfigParser.SafeConfigParser()
	config.read(constants._user_settings_)
	backend = create_backend(config)
	notifyUser = is_changed(config, backend)

	if notifyUser:
		logging.info("Changed")
		import led_handler
		led = led_handler.LedHandler()
		led.on()
	else:
		logging.info("No Change")


if __name__ == "__main__":
	logFormat = '(%(relativeCreated)5d) %(levelname)-5s %(threadName)s.%(name)s.%(funcName)s: %(message)s'
	logging.basicConfig(level=logging.DEBUG, format=logFormat)
	rotating = logging.handlers.RotatingFileHandler(constants._notifier_logpath_, maxBytes=512*1024, backupCount=1)
	rotating.setFormatter(logging.Formatter(logFormat))
	root = logging.getLogger()
	root.addHandler(rotating)
	logging.info("Notifier %s-%s" % (constants.__version__, constants.__build__))
	logging.info("OS: %s" % (os.uname()[0], ))
	logging.info("Kernel: %s (%s) for %s" % os.uname()[2:])
	logging.info("Hostname: %s" % os.uname()[1])
	try:
		notify_on_change()
	except:
		logging.exception("Error")
		raise
