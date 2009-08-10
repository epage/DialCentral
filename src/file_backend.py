#!/usr/bin/python

"""
DialCentral - Front end for Google's Grand Central service.
Copyright (C) 2008  Eric Warnke ericew AT gmail DOT com

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

Filesystem backend for contact support
"""


import os
import re
import csv


class CsvAddressBook(object):
	"""
	Currently supported file format
	@li Has the first line as a header
	@li Escapes with quotes
	@li Comma as delimiter
	@li Column 0 is name, column 1 is number
	"""

	_nameRe = re.compile("name", re.IGNORECASE)
	_phoneRe = re.compile("phone", re.IGNORECASE)
	_mobileRe = re.compile("mobile", re.IGNORECASE)

	def __init__(self, csvPath):
		self.__csvPath = csvPath
		self.__contacts = list(
			self.read_csv(csvPath)
		)

	@classmethod
	def read_csv(cls, csvPath):
		try:
			csvReader = iter(csv.reader(open(csvPath, "rU")))
		except IOError, e:
			if e.errno != 2:
				raise
			return

		header = csvReader.next()
		nameColumn, phoneColumns = cls._guess_columns(header)

		yieldCount = 0
		for row in csvReader:
			contactDetails = []
			for (phoneType, phoneColumn) in phoneColumns:
				try:
					if len(row[phoneColumn]) == 0:
						continue
					contactDetails.append((phoneType, row[phoneColumn]))
				except IndexError:
					pass
			if len(contactDetails) != 0:
				yield str(yieldCount), row[nameColumn], contactDetails
				yieldCount += 1

	@classmethod
	def _guess_columns(cls, row):
		names = []
		phones = []
		for i, item in enumerate(row):
			if cls._nameRe.search(item) is not None:
				names.append((item, i))
			elif cls._phoneRe.search(item) is not None:
				phones.append((item, i))
			elif cls._mobileRe.search(item) is not None:
				phones.append((item, i))
		if len(names) == 0:
			names.append(("Name", 0))
		if len(phones) == 0:
			phones.append(("Phone", 1))

		return names[0][1], phones

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
		return iter(self.__contacts[contactId][2])


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
		for root, dirs, filenames in os.walk(self.__path):
			for filename in filenames:
				try:
					name, ext = filename.rsplit(".", 1)
				except ValueError:
					continue

				if ext in self.FILETYPE_SUPPORT:
					yield self, os.path.join(root, filename), name

	def open_addressbook(self, bookId):
		name, ext = bookId.rsplit(".", 1)
		assert ext in self.FILETYPE_SUPPORT, "Unsupported file extension %s" % ext
		return self.FILETYPE_SUPPORT[ext](bookId)

	@staticmethod
	def factory_name():
		return "File"


def print_filebooks(contactPath = None):
	"""
	Included here for debugging.

	Either insert it into the code or launch python with the "-i" flag
	"""
	if contactPath is None:
		contactPath = os.path.join(os.path.expanduser("~"), ".dialcentral", "contacts")

	abf = FilesystemAddressBookFactory(contactPath)
	for book in abf.get_addressbooks():
		ab = abf.open_addressbook(book[1])
		print book
		for contact in ab.get_contacts():
			print "\t", contact
			for details in ab.get_contact_details(contact[0]):
				print "\t\t", details
