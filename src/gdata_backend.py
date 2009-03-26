#!/usr/bin/python

import sys
sys.path.insert(0,"../gdata/src/")


try:
	import atom
	import gdata
	gdata.contacts
except (ImportError, AttributeError):
	atom = None
	gdata = None


class GDataAddressBook(object):
	"""
	"""

	def __init__(self, client, id = None):
		self._client = client
		self._id = id
		self._contacts = []

	def clear_caches(self):
		del self._contacts[:]

	@staticmethod
	def factory_name():
		return "GData"

	@staticmethod
	def contact_source_short_name(contactId):
		return "gd"

	def get_contacts(self):
		"""
		@returns Iterable of (contact id, contact name)
		"""
		return []

	def get_contact_details(self, contactId):
		"""
		@returns Iterable of (Phone Type, Phone Number)
		"""
		return []

	def _get_contacts(self):
		if len(self._contacts) != 0:
			return self._contacts
		feed = self._get_feed()
		for entry in feed:
			name = entry.title.text
			print name
			for extendedProperty in entry.extended_property:
				if extendedProperty.value:
					print extendedProperty.value
				else:
					print extendedProperty.GetXmlBlobString()

	def _get_feed(self):
		if self._id is None:
			return self._client.GetContactsFeed()
		else:
			pass


class GDataAddressBookFactory(object):

	def __init__(self, username, password):
		self._username = username
		self._password = password
		self._client = None

		if gdata is None:
			return
		self._client = gdata.contacts.service.ContactsService()
		self._client.email = username
		self._client.password = password
		self._client.source = "DialCentra"
		self._client.ProgrammaticLogin()

	def clear_caches(self):
		if gdata is None:
			return

	def get_addressbooks(self):
		"""
		@returns Iterable of (Address Book Factory, Book Id, Book Name)
		"""
		if gdata is None:
			return
		feed = self._client.GetGroupsFeed()
		for entry in feed:
			id = entry.id.text
			name = entry.title.text
			yield self, id, name
		yield self, "all", "All"

	def open_addressbook(self, bookId):
		if gdata is None:
			return
		if bookId == "all":
			return GDataAddressBook(self._client)
		else:
			return GDataAddressBook(self._client, bookId)

	@staticmethod
	def factory_name():
		return "GData"


def print_gbooks(username, password):
	"""
	Included here for debugging.

	Either insert it into the code or launch python with the "-i" flag
	"""
	abf = GDataAddressBookFactory(username, password)
	for book in abf.get_addressbooks():
		ab = abf.open_addressbook(book[1])
		print book
		for contact in ab.get_contacts():
			print "\t", contact
			for details in ab.get_contact_details(contact[0]):
				print "\t\t", details
