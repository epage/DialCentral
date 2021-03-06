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

from __future__ import with_statement

import os
import csv


def try_unicode(s):
	try:
		return s.decode("UTF-8")
	except UnicodeDecodeError:
		return s


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

	def update_account(self, force = True):
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
			f = open(csvPath, "rU")
			csvReader = iter(csv.reader(f))
		except IOError, e:
			if e.errno == 2:
				return
			raise

		header = csvReader.next()
		nameColumns, nameFallbacks, phoneColumns = self._guess_columns(header)

		yieldCount = 0
		for row in csvReader:
			contactDetails = []
			for (phoneType, phoneColumn) in phoneColumns:
				try:
					if len(row[phoneColumn]) == 0:
						continue
					contactDetails.append({
						"phoneType": try_unicode(phoneType),
						"phoneNumber": row[phoneColumn],
					})
				except IndexError:
					pass
			if 0 < len(contactDetails):
				nameParts = (row[i].strip() for i in nameColumns)
				nameParts = (part for part in nameParts if part)
				fullName = " ".join(nameParts).strip()
				if not fullName:
					for fallbackColumn in nameFallbacks:
						if row[fallbackColumn].strip():
							fullName = row[fallbackColumn].strip()
							break
					else:
						fullName = "Unknown"
				fullName = try_unicode(fullName)
				yield str(yieldCount), {
					"contactId": "%s-%d" % (self._name, yieldCount),
					"name": fullName,
					"numbers": contactDetails,
				}
				yieldCount += 1

	@classmethod
	def _guess_columns(cls, row):
		firstMiddleLast = [-1, -1, -1]
		names = []
		nameFallbacks = []
		phones = []
		for i, item in enumerate(row):
			lowerItem = item.lower()
			if 0 <= lowerItem.find("name"):
				names.append((item, i))

				if 0 <= lowerItem.find("couple"):
					names.insert(0, (item, i))

				if 0 <= lowerItem.find("first") or 0 <= lowerItem.find("given"):
					firstMiddleLast[0] = i
				elif 0 <= lowerItem.find("middle"):
					firstMiddleLast[1] = i
				elif 0 <= lowerItem.find("last") or 0 <= lowerItem.find("family"):
					firstMiddleLast[2] = i
			elif 0 <= lowerItem.find("phone"):
				phones.append((item, i))
			elif 0 <= lowerItem.find("mobile"):
				phones.append((item, i))
			elif 0 <= lowerItem.find("email") or 0 <= lowerItem.find("e-mail"):
				nameFallbacks.append(i)
		if len(names) == 0:
			names.append(("Name", 0))
		if len(phones) == 0:
			phones.append(("Phone", 1))

		nameColumns = [i for i in firstMiddleLast if 0 <= i]
		if len(nameColumns) < 2:
			del nameColumns[:]
			nameColumns.append(names[0][1])

		return nameColumns, nameFallbacks, phones


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
