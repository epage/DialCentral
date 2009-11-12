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
"""


class NullDialer(object):

	def __init__(self):
		pass

	def is_authed(self, force = False):
		return False

	def login(self, username, password):
		return self.is_authed()

	def logout(self):
		self.clear_caches()

	def dial(self, number):
		return True

	def send_sms(self, number, message):
		raise NotImplementedError("SMS Is Not Supported")

	def clear_caches(self):
		pass

	def is_valid_syntax(self, number):
		"""
		@returns If This number be called ( syntax validation only )
		"""
		return False

	def get_account_number(self):
		"""
		@returns The grand central phone number
		"""
		return ""

	def set_sane_callback(self):
		pass

	def get_callback_numbers(self):
		return {}

	def set_callback_number(self, callbacknumber):
		return True

	def get_callback_number(self):
		return ""

	def get_recent(self):
		return ()

	def get_addressbooks(self):
		return ()

	def open_addressbook(self, bookId):
		return self

	@staticmethod
	def contact_source_short_name(contactId):
		return "ERROR"

	@staticmethod
	def factory_name():
		return "ERROR"

	def get_contacts(self):
		return ()

	def get_contact_details(self, contactId):
		return ()

	def get_messages(self):
		return ()


class NullAddressBook(object):
	"""
	Minimal example of both an addressbook factory and an addressbook
	"""

	def clear_caches(self):
		pass

	def get_addressbooks(self):
		"""
		@returns Iterable of (Address Book Factory, Book Id, Book Name)
		"""
		yield self, "", "None"

	def open_addressbook(self, bookId):
		return self

	@staticmethod
	def contact_source_short_name(contactId):
		return ""

	@staticmethod
	def factory_name():
		return ""

	@staticmethod
	def get_contacts():
		"""
		@returns Iterable of (contact id, contact name)
		"""
		return []

	@staticmethod
	def get_contact_details(contactId):
		"""
		@returns Iterable of (Phone Type, Phone Number)
		"""
		return []
