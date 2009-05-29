from __future__ import with_statement

import os
import warnings

import test_utils

import sys
sys.path.append("../src")

import file_backend


def test_factory():
	warnings.simplefilter("always")
	try:
		csvPath = os.path.join(os.path.dirname(__file__), "basic_data")
		factory = file_backend.FilesystemAddressBookFactory(csvPath)
		assert factory.factory_name() == "File"
		abooks = list(factory.get_addressbooks())
		abooks.sort()
		assert len(abooks) == 4
		abookNames = [abook[2] for abook in abooks]
		assert abookNames == ["basic", "empty", "google", "grandcentral"], "%s" % abookNames

		for abook_factory, abookId, abookName in abooks:
			abook = abook_factory.open_addressbook(abookId)
			assert isinstance(abook, file_backend.CsvAddressBook)
	finally:
		warnings.resetwarnings()


def test_nonexistent_csv():
	warnings.simplefilter("always")
	try:
		csvPath = os.path.join(os.path.dirname(__file__), "basic_data", "nonexistent.csv")
		abook = file_backend.CsvAddressBook(csvPath)

		assert abook.factory_name() == "csv"

		contacts = list(abook.get_contacts())
		assert len(contacts) == 0
	finally:
		warnings.resetwarnings()


def test_empty_csv():
	warnings.simplefilter("always")
	try:
		csvPath = os.path.join(os.path.dirname(__file__), "basic_data", "empty.csv")
		abook = file_backend.CsvAddressBook(csvPath)

		assert abook.factory_name() == "csv"

		contacts = list(abook.get_contacts())
		assert len(contacts) == 0
	finally:
		warnings.resetwarnings()


def test_basic_csv():
	warnings.simplefilter("always")
	try:
		csvPath = os.path.join(os.path.dirname(__file__), "basic_data", "basic.csv")
		abook = file_backend.CsvAddressBook(csvPath)

		assert abook.factory_name() == "csv"

		contacts = list(abook.get_contacts())
		contacts.sort()
		assert len(contacts) == 1

		contactId, contactName = contacts[0]
		assert contactName == "Last, First"
		assert abook.contact_source_short_name(contactId) == "csv"

		details = list(abook.get_contact_details(contactId))
		assert len(details) == 1
		details.sort()
		assert details == [("phone", "555-123-4567")], "%s" % details
	finally:
		warnings.resetwarnings()


def test_google_csv():
	warnings.simplefilter("always")
	try:
		csvPath = os.path.join(os.path.dirname(__file__), "basic_data", "google.csv")
		abook = file_backend.CsvAddressBook(csvPath)

		assert abook.factory_name() == "csv"

		contacts = list(abook.get_contacts())
		contacts.sort()
		assert len(contacts) == 2

		contactId, contactName = contacts[0]
		assert contactName == "First Last"
		assert abook.contact_source_short_name(contactId) == "csv"

		details = list(abook.get_contact_details(contactId))
		assert len(details) == 2
		details.sort()
		assert details == [
			("Section 2 - Mobile", "5551234567"),
			("Section 2 - Phone", "17471234567"),
		], "%s" % details

		contactId, contactName = contacts[1]
		assert contactName == "First1 Last"
		assert abook.contact_source_short_name(contactId) == "csv"

		details = list(abook.get_contact_details(contactId))
		assert len(details) == 1
		details.sort()
		assert details == [("Section 1 - Mobile", "5557654321")], "%s" % details
	finally:
		warnings.resetwarnings()


def test_grandcentral_csv():
	warnings.simplefilter("always")
	try:
		csvPath = os.path.join(os.path.dirname(__file__), "basic_data", "grandcentral.csv")
		abook = file_backend.CsvAddressBook(csvPath)

		assert abook.factory_name() == "csv"

		contacts = list(abook.get_contacts())
		contacts.sort()
		assert len(contacts) == 2

		contactId, contactName = contacts[0]
		assert contactName == "First Last"
		assert abook.contact_source_short_name(contactId) == "csv"

		details = list(abook.get_contact_details(contactId))
		assert len(details) == 3
		details.sort()
		assert details == [
			("Business Phone", "5559988899"),
			("Home Phone", "5559983254"),
			("Mobile Phone", "5554023626"),
		], "%s" % details

		contactId, contactName = contacts[1]
		assert contactName == "First1 Last"
		assert abook.contact_source_short_name(contactId) == "csv"

		details = list(abook.get_contact_details(contactId))
		assert len(details) == 1
		details.sort()
		assert details == [("Home Phone", "5556835460")], "%s" % details
	finally:
		warnings.resetwarnings()
