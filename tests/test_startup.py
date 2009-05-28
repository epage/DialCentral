from __future__ import with_statement

import os
import time

import test_utils

import sys
sys.path.append("../src")

import dc_glade


def startup(factory):
	handle = factory()
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


def test_startup_with_no_data_dir_with_dummy_hildon():
	dc_glade.Dialcentral._data_path = os.path.join(os.path.dirname(__file__), "notexistent_data")
	dc_glade.Dialcentral._user_settings = "%s/settings.ini" % dc_glade.Dialcentral._data_path

	try:
		sys.path.insert(0, "dummy_hildon")
		startup(dc_glade.Dialcentral)
		sys.path.remove("dummy_hildon")
	finally:
		os.remove(dc_glade.Dialcentral._user_settings)
		os.removedirs(dc_glade.Dialcentral._data_path)


def test_startup_with_no_data_dir():
	dc_glade.Dialcentral._data_path = os.path.join(os.path.dirname(__file__), "notexistent_data")
	dc_glade.Dialcentral._user_settings = "%s/settings.ini" % dc_glade.Dialcentral._data_path

	try:
		startup(dc_glade.Dialcentral)
	finally:
		os.remove(dc_glade.Dialcentral._user_settings)
		os.removedirs(dc_glade.Dialcentral._data_path)


def test_startup_with_empty_data_dir():
	dc_glade.Dialcentral._data_path = os.path.join(os.path.dirname(__file__), "empty_data")
	dc_glade.Dialcentral._user_settings = "%s/settings.ini" % dc_glade.Dialcentral._data_path

	try:
		startup(dc_glade.Dialcentral)
	finally:
		os.remove(dc_glade.Dialcentral._user_settings)
		os.removedirs(dc_glade.Dialcentral._data_path)


def test_startup_with_basic_data_dir():
	dc_glade.Dialcentral._data_path = os.path.join(os.path.dirname(__file__), "basic_data")
	dc_glade.Dialcentral._user_settings = "%s/settings.ini" % dc_glade.Dialcentral._data_path

	startup(dc_glade.Dialcentral)
