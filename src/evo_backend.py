#!/usr/bin/python

# GC Dialer - Front end for Google's Grand Central service.
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
Evolution Contact Support
"""


try:
	import evolution
except ImportError:
	evolution = None


class EvolutionAddressBook(object):

	def __init__(self, bookId = None):
		if not self.is_supported():
			return

		self._phoneTypes = None
		self._bookId = bookId if bookId is not None else self.get_addressbooks().next()[1]
		self._book = evolution.ebook.open_addressbook(self._bookId)
	
	@classmethod
	def is_supported(cls):
		return evolution is not None

	def get_addressbooks(self):
		"""
		@returns Iterable of (Address Book Factory, Book Id, Book Name)
		"""
		if not self.is_supported():
			return

		for bookId in evolution.ebook.list_addressbooks():
			yield self, bookId[1], bookId[0]
	
	def open_addressbook(self, bookId):
		self._bookId = bookId
		self._book = evolution.ebook.open_addressbook(self._bookId)
		return self

	@staticmethod
	def factory_name():
		return "Evo"

	def get_contacts(self):
		"""
		@returns Iterable of (contact id, contact name)
		"""
		if not self.is_supported():
			return

		for contact in self._book.get_all_contacts():
			yield contact.get_uid(), contact.props.full_name
	
	def get_contact_details(self, contactId):
		"""
		@returns Iterable of (Phone Type, Phone Number)
		"""
		contact = self._book.get_contact(contactId)

		if self._phoneTypes is None and contact is not None:
			self._phoneTypes = [pt for pt in dir(contact.props) if "phone" in pt.lower()]

		for phoneType in self._phoneTypes:
			phoneNumber = getattr(contact.props, phoneType)
			if isinstance(phoneNumber, str):
				yield phoneType, phoneNumber

def print_addressbooks():
	"""
	Included here for debugging.

	Either insert it into the code or launch python with the "-i" flag
	"""
	if not EvolutionAddressBook.is_supported():
		print "No Evolution Support"
		return

	eab = EvolutionAddressBook()
	for book in eab.get_addressbooks():
		eab = eab.open_addressbook(book[1])
		print book
		for contact in eab.get_contacts():
			print "\t", contact
			for details in eab.get_contact_details(contact[0]):
				print "\t\t", details
