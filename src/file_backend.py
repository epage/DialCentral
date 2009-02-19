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
Filesystem backend for contact support
"""


import os
import csv


class CsvAddressBook(object):
	"""
	Currently supported file format
	@li Has the first line as a header
	@li Escapes with quotes
	@li Comma as delimiter
	@li Column 0 is name, column 1 is number
	"""

	def __init__(self, csvPath):
		self.__csvPath = csvPath
		self.__contacts = list(
			self.read_csv(csvPath)
		)

	@staticmethod
	def read_csv(csvPath):
		csvReader = iter(csv.reader(open(csvPath, "rU")))
		csvReader.next()
		for i, row in enumerate(csvReader):
			yield str(i), row[0], row[1]

	def clear_caches(self):
		pass

	@staticmethod
	def factory_name():
		return "csv"

	@staticmethod
	def contact_source_short_name(contactId):
		return "csv"

	def get_contacts(self):
		"""
		@returns Iterable of (contact id, contact name)
		"""
		for contact in self.__contacts:
			yield contact[0:2]

	def get_contact_details(self, contactId):
		"""
		@returns Iterable of (Phone Type, Phone Number)
		"""
		contactId = int(contactId)
		yield "", self.__contacts[contactId][2]


class FilesystemAddressBookFactory(object):

	FILETYPE_SUPPORT = {
		"csv": CsvAddressBook,
	}

	def __init__(self, path):
		self.__path = path

	def clear_caches(self):
		pass

	def get_addressbooks(self):
		"""
		@returns Iterable of (Address Book Factory, Book Id, Book Name)
		"""
		for root, dirs, files in os.walk(self.__path):
			for file in files:
				name, ext = file.rsplit(".", 1)
				if ext in self.FILETYPE_SUPPORT:
					yield self, os.path.join(root, file), name

	def open_addressbook(self, bookId):
		name, ext = bookId.rsplit(".", 1)
		assert ext in self.FILETYPE_SUPPORT
		return self.FILETYPE_SUPPORT[ext](bookId)

	@staticmethod
	def factory_name():
		return "File"


def print_books():
	"""
	Included here for debugging.

	Either insert it into the code or launch python with the "-i" flag
	"""
	eab = FilesystemAddressBookFactory(os.path.expanduser("~/Desktop"))
	for book in eab.get_addressbooks():
		eab = eab.open_addressbook(book[1])
		print book
		for contact in eab.get_contacts():
			print "\t", contact
			for details in eab.get_contact_details(contact[0]):
				print "\t\t", details
