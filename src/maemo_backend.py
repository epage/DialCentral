#!/usr/bin/python

# DialCentral - Front end for Google's Grand Central service.
# Copyright (C) 2008  Eric Warnke ericew AT gmail DOT com
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA


"""
Maemo Contacts Support
"""


import warnings

try:
	import abook
except ImportError:
	abook = None

try:
	import evolution.ebook as ebook
except ImportError:
	ebook = None


class MaemoAddressBook(object):
	"""
	@note Combined the factory and the addressbook for "simplicity" and "cutting down" the number of allocations/deallocations
	"""

	def __init__(self, contextName, context):
		if not self.is_supported():
			return

		abook.init_with_name(contextName, context)
		self._book = abook.all_group_get()

	@classmethod
	def is_supported(cls):
		return abook is not None and ebook is not None

	def get_addressbooks(self):
		"""
		@returns Iterable of (Address Book Factory, Book Id, Book Name)
		"""
		if not self.is_supported():
			return

		yield self, "", ""

	def open_addressbook(self, bookId):
		return self

	@staticmethod
	def contact_source_short_name(contactId):
		return "M"

	@staticmethod
	def factory_name():
		return "Maemo"

	def get_contacts(self):
		"""
		@returns Iterable of (contact id, contact name)
		"""
		if not self.is_supported():
			return
		pass

	def get_contact_details(self, contactId):
		"""
		@returns Iterable of (Phone Type, Phone Number)
		"""
		pass


def print_maemobooks():
	"""
	Included here for debugging.

	Either insert it into the code or launch python with the "-i" flag
	"""
	if not MaemoAddressBook.is_supported():
		print "No GMail Support"
		return

	mab = MaemoAddressBook()
	for book in mab.get_addressbooks():
		mab = mab.open_addressbook(book[1])
		print book
		for contact in mab.get_contacts():
			print "\t", contact
			for details in mab.get_contact_details(contact[0]):
				print "\t\t", details
	print mab._gmailContacts

