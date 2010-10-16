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
import csv


class CsvAddressBook(object):
	"""
	Currently supported file format
	@li Has the first line as a header
	@li Escapes with quotes
	@li Comma as delimiter
	@li Column 0 is name, column 1 is number
	"""

	def __init__(self, name, csvPath):
		self._name = name
		self._csvPath = csvPath
		self._contacts = {}

	@property
	def name(self):
		return self._name

	def update_contacts(self, force = True):
		if not force or not self._contacts:
			return
		self._contacts = dict(
			self._read_csv(self._csvPath)
		)

	def get_contacts(self):
		"""
		@returns Iterable of (contact id, contact name)
		"""
		if not self._contacts:
			self._contacts = dict(
				self._read_csv(self._csvPath)
			)
		return self._contacts

	def _read_csv(self, csvPath):
		try:
			csvReader = iter(csv.reader(open(csvPath, "rU")))
		except IOError, e:
			if e.errno != 2:
				raise
			return

		header = csvReader.next()
		nameColumn, phoneColumns = self._guess_columns(header)

		yieldCount = 0
		for row in csvReader:
			contactDetails = []
			for (phoneType, phoneColumn) in phoneColumns:
				try:
					if len(row[phoneColumn]) == 0:
						continue
					contactDetails.append({
						"phoneType": phoneType,
						"phoneNumber": row[phoneColumn],
					})
				except IndexError:
					pass
			if 0 < len(contactDetails):
				yield str(yieldCount), {
					"contactId": "%s-%d" % (self._name, yieldCount),
					"name": row[nameColumn],
					"numbers": contactDetails,
				}
				yieldCount += 1

	@classmethod
	def _guess_columns(cls, row):
		names = []
		phones = []
		for i, item in enumerate(row):
			if 0 <= item.lower().find("name"):
				names.append((item, i))
			elif 0 <= item.lower().find("phone"):
				phones.append((item, i))
			elif 0 <= item.lower().find("mobile"):
				phones.append((item, i))
		if len(names) == 0:
			names.append(("Name", 0))
		if len(phones) == 0:
			phones.append(("Phone", 1))

		return names[0][1], phones


class FilesystemAddressBookFactory(object):

	FILETYPE_SUPPORT = {
		"csv": CsvAddressBook,
	}

	def __init__(self, path):
		self._path = path

	def get_addressbooks(self):
		for root, dirs, filenames in os.walk(self._path):
			for filename in filenames:
				try:
					name, ext = filename.rsplit(".", 1)
				except ValueError:
					continue

				try:
					cls = self.FILETYPE_SUPPORT[ext]
				except KeyError:
					continue
				yield cls(name, os.path.join(root, filename))
