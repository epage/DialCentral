#!/usr/bin/env python

from __future__ import with_statement
from __future__ import division

import logging

import util.qt_compat as qt_compat
if qt_compat.USES_PYSIDE:
	import QtMobility.Contacts as _QtContacts
	QtContacts = _QtContacts
else:
	QtContacts = None

import null_backend


_moduleLogger = logging.getLogger(__name__)


class QtContactsAddressBook(object):

	def __init__(self, name, uri):
		self._name = name
		self._uri = uri
		self._manager = QtContacts.QContactManager.fromUri(uri)
		self._contacts = None

	@property
	def name(self):
		return self._name

	@property
	def error(self):
		return self._manager.error()

	def update_account(self, force = True):
		if not force and self._contacts is not None:
			return
		self._contacts = dict(self._get_contacts())

	def get_contacts(self):
		if self._contacts is None:
			self._contacts = dict(self._get_contacts())
		return self._contacts

	def _get_contacts(self):
		contacts = self._manager.contacts()
		for contact in contacts:
			contactId = contact.localId()
			contactName = contact.displayLabel()
			phoneDetails = contact.details(QtContacts.QContactPhoneNumber().DefinitionName)
			phones = [{"phoneType": "Phone", "phoneNumber": phone.value(QtContacts.QContactPhoneNumber().FieldNumber)} for phone in phoneDetails]
			contactDetails = phones
			if 0 < len(contactDetails):
				yield str(contactId), {
					"contactId": str(contactId),
					"name": contactName,
					"numbers": contactDetails,
				}


class _QtContactsAddressBookFactory(object):

	def __init__(self):
		self._availableManagers = {}

		availableMgrs = QtContacts.QContactManager.availableManagers()
		availableMgrs.remove("invalid")
		for managerName in availableMgrs:
			params = {}
			managerUri = QtContacts.QContactManager.buildUri(managerName, params)
			self._availableManagers[managerName] =  managerUri

	def get_addressbooks(self):
		for name, uri in self._availableManagers.iteritems():
			book = QtContactsAddressBook(name, uri)
			if book.error:
				_moduleLogger.info("Could not load %r due to %r" % (name, book.error))
			else:
				yield book


class _EmptyAddressBookFactory(object):

	def get_addressbooks(self):
		if False:
			yield None


if QtContacts is not None:
	QtContactsAddressBookFactory = _QtContactsAddressBookFactory
else:
	QtContactsAddressBookFactory = _EmptyAddressBookFactory
	_moduleLogger.info("QtContacts support not available")


if __name__ == "__main__":
	factory = QtContactsAddressBookFactory()
	books = factory.get_addressbooks()
	for book in books:
		print book.name
		print book.get_contacts()
