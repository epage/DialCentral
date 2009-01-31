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
GMail Contacts Support
"""


import warnings


try:
	import libgmail
except ImportError:
	libgmail = None


class GMailAddressBook(object):
	"""
	@note Combined the factory and the addressbook for "simplicity" and "cutting down" the number of allocations/deallocations
	"""

	def __init__(self, username, password):
		if not self.is_supported():
			return

		self._account = libgmail.GmailAccount(username, password)
		self._gmailContacts = self._account.getContacts()
	
	@classmethod
	def is_supported(cls):
		return libgmail is not None

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
		return "G"

	@staticmethod
	def factory_name():
		return "GMail"

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


def print_gbooks(username, password):
	"""
	Included here for debugging.

	Either insert it into the code or launch python with the "-i" flag
	"""
	if not GMailAddressBook.is_supported():
		print "No GMail Support"
		return

	gab = GMailAddressBook(username, password)
	for book in gab.get_addressbooks():
		gab = gab.open_addressbook(book[1])
		print book
		for contact in gab.get_contacts():
			print "\t", contact
			for details in gab.get_contact_details(contact[0]):
				print "\t\t", details
	print gab._gmailContacts
