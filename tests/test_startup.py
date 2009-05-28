from __future__ import with_statement

import os
import time

import test_utils

import sys
sys.path.append("../src")

import dc_glade


def test_startup_with_no_data_dir():
	dc_glade.Dialcentral._data_path = os.path.join(os.path.dirname(__file__), "notexistent_data")
	dc_glade.Dialcentral._user_settings = "%s/settings.ini" % dc_glade.Dialcentral._data_path

	try:
		handle = dc_glade.Dialcentral()
		with test_utils.expected(AssertionError("Attempting login before app is fully loaded")):
			handle.refresh_session()

		for i in xrange(10):
			if handle._initDone:
				print "Completed init on iteration %d" % i
				break
			time.sleep(1)
		assert handle._initDone

		with test_utils.expected(RuntimeError("Login Failed")):
			handle.refresh_session()

		handle._save_settings()

		del handle
	finally:
		os.remove(dc_glade.Dialcentral._user_settings)
		os.removedirs(dc_glade.Dialcentral._data_path)


def test_startup_with_empty_data_dir():
	dc_glade.Dialcentral._data_path = os.path.join(os.path.dirname(__file__), "empty_data")
	dc_glade.Dialcentral._user_settings = "%s/settings.ini" % dc_glade.Dialcentral._data_path

	try:
		os.makedirs(dc_glade.Dialcentral._data_path)

		handle = dc_glade.Dialcentral()
		with test_utils.expected(AssertionError("Attempting login before app is fully loaded")):
			handle.refresh_session()

		for i in xrange(10):
			if handle._initDone:
				print "Completed init on iteration %d" % i
				break
			time.sleep(1)
		assert handle._initDone

		with test_utils.expected(RuntimeError("Login Failed")):
			handle.refresh_session()

		handle._save_settings()

		del handle
	finally:
		os.remove(dc_glade.Dialcentral._user_settings)
		os.removedirs(dc_glade.Dialcentral._data_path)


def test_startup_with_basic_data_dir():
	dc_glade.Dialcentral._data_path = os.path.join(os.path.dirname(__file__), "basic_data")
	dc_glade.Dialcentral._user_settings = "%s/settings.ini" % dc_glade.Dialcentral._data_path

	handle = dc_glade.Dialcentral()
	with test_utils.expected(AssertionError("Attempting login before app is fully loaded")):
		handle.refresh_session()

	for i in xrange(10):
		if handle._initDone:
			print "Completed init on iteration %d" % i
			break
		time.sleep(1)
	assert handle._initDone

	with test_utils.expected(RuntimeError("Login Failed")):
		handle.refresh_session()

	handle._save_settings()

	del handle
