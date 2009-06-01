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

Grandcentral backend code
"""


import os
import re
import urllib
import urllib2
import time
import warnings
import traceback
from xml.sax import saxutils

import browser_emu


class GCDialer(object):
	"""
	This class encapsulates all of the knowledge necessary to interace with the grandcentral servers
	the functions include login, setting up a callback number, and initalting a callback
	"""

	_gcDialingStrRe = re.compile("This may take a few seconds", re.M)
	_accessTokenRe = re.compile(r"""<input type="hidden" name="a_t" [^>]*value="(.*)"/>""")
	_isLoginPageRe = re.compile(r"""<form method="post" action="https://www.grandcentral.com/mobile/account/login">""")
	_callbackRe = re.compile(r"""name="default_number" value="(\d+)" />\s+(.*)\s$""", re.M)
	_accountNumRe = re.compile(r"""<input type="hidden" name="gcentral_num" [^>]*value="(.*)"/>""")
	_inboxRe = re.compile(r"""<td>.*?(voicemail|received|missed|call return).*?</td>\s+<td>\s+<font size="2">\s+(.*?)\s+&nbsp;\|&nbsp;\s+<a href="/mobile/contacts/.*?">(.*?)\s?</a>\s+<br/>\s+(.*?)\s?<a href=""", re.S)
	_contactsRe = re.compile(r"""<a href="/mobile/contacts/detail/(\d+)">(.*?)</a>""", re.S)
	_contactsNextRe = re.compile(r""".*<a href="/mobile/contacts(\?page=\d+)">Next</a>""", re.S)
	_contactDetailPhoneRe = re.compile(r"""(\w+):[0-9\-\(\) \t]*?<a href="/mobile/calls/click_to_call\?destno=(\d+).*?">call</a>""", re.S)

	_validateRe = re.compile("^[0-9]{10,}$")

	_forwardselectURL = "http://www.grandcentral.com/mobile/settings/forwarding_select"
	_loginURL = "https://www.grandcentral.com/mobile/account/login"
	_setforwardURL = "http://www.grandcentral.com/mobile/settings/set_forwarding?from=settings"
	_clicktocallURL = "http://www.grandcentral.com/mobile/calls/click_to_call?a_t=%s&destno=%s"
	_inboxallURL = "http://www.grandcentral.com/mobile/messages/inbox?types=all"
	_contactsURL = "http://www.grandcentral.com/mobile/contacts"
	_contactDetailURL = "http://www.grandcentral.com/mobile/contacts/detail"

	def __init__(self, cookieFile = None):
		# Important items in this function are the setup of the browser emulation and cookie file
		self._browser = browser_emu.MozillaEmulator(1)
		if cookieFile is None:
			cookieFile = os.path.join(os.path.expanduser("~"), ".gc_cookies.txt")
		self._browser.cookies.filename = cookieFile
		if os.path.isfile(cookieFile):
			self._browser.cookies.load()

		self._accessToken = None
		self._accountNum = ""
		self._lastAuthed = 0.0
		self._callbackNumber = ""
		self._callbackNumbers = {}

		self.__contacts = None

	def is_authed(self, force = False):
		"""
		Attempts to detect a current session and pull the auth token ( a_t ) from the page.
		@note Once logged in try not to reauth more than once a minute.
		@returns If authenticated
		"""

		if (time.time() - self._lastAuthed) < 60 and not force:
			return True

		try:
			forwardSelectionPage = self._browser.download(self._forwardselectURL)
		except urllib2.URLError, e:
			warnings.warn(traceback.format_exc())
			return False

		if self._isLoginPageRe.search(forwardSelectionPage) is not None:
			return False

		try:
			self._grab_token(forwardSelectionPage)
		except StandardError, e:
			warnings.warn(traceback.format_exc())
			return False

		self._browser.cookies.save()
		self._lastAuthed = time.time()
		return True

	def login(self, username, password):
		"""
		Attempt to login to grandcentral
		@returns Whether login was successful or not
		"""
		if self.is_authed():
			return True

		loginPostData = urllib.urlencode( {'username' : username , 'password' : password } )

		try:
			loginSuccessOrFailurePage = self._browser.download(self._loginURL, loginPostData)
		except urllib2.URLError, e:
			warnings.warn(traceback.format_exc())
			raise RuntimeError("%s is not accesible" % self._loginURL)

		return self.is_authed()

	def logout(self):
		self._lastAuthed = 0.0
		self._browser.cookies.clear()
		self._browser.cookies.save()

		self.clear_caches()

	def dial(self, number):
		"""
		This is the main function responsible for initating the callback
		"""
		if not self.is_valid_syntax(number):
			raise ValueError('Number is not valid: "%s"' % number)
		elif not self.is_authed():
			raise RuntimeError("Not Authenticated")

		if len(number) == 11 and number[0] == 1:
			# Strip leading 1 from 11 digit dialing
			number = number[1:]

		try:
			callSuccessPage = self._browser.download(
				self._clicktocallURL % (self._accessToken, number),
				None,
				{'Referer' : 'http://www.grandcentral.com/mobile/messages'}
			)
		except urllib2.URLError, e:
			warnings.warn(traceback.format_exc())
			raise RuntimeError("%s is not accesible" % self._clicktocallURL)

		if self._gcDialingStrRe.search(callSuccessPage) is None:
			raise RuntimeError("Grand Central returned an error")

		return True

	def send_sms(self, number, message):
		raise NotImplementedError("SMS Is Not Supported by GrandCentral")

	def clear_caches(self):
		self.__contacts = None

	def is_valid_syntax(self, number):
		"""
		@returns If This number be called ( syntax validation only )
		"""
		return self._validateRe.match(number) is not None

	def get_account_number(self):
		"""
		@returns The grand central phone number
		"""
		return self._accountNum

	def set_sane_callback(self):
		"""
		Try to set a sane default callback number on these preferences
		1) 1747 numbers ( Gizmo )
		2) anything with gizmo in the name
		3) anything with computer in the name
		4) the first value
		"""
		numbers = self.get_callback_numbers()

		for number, description in numbers.iteritems():
			if re.compile(r"""1747""").match(number) is not None:
				self.set_callback_number(number)
				return

		for number, description in numbers.iteritems():
			if re.compile(r"""gizmo""", re.I).search(description) is not None:
				self.set_callback_number(number)
				return

		for number, description in numbers.iteritems():
			if re.compile(r"""computer""", re.I).search(description) is not None:
				self.set_callback_number(number)
				return

		for number, description in numbers.iteritems():
			self.set_callback_number(number)
			return

	def get_callback_numbers(self):
		"""
		@returns a dictionary mapping call back numbers to descriptions
		@note These results are cached for 30 minutes.
		"""
		if time.time() - self._lastAuthed < 1800 or self.is_authed():
			return self._callbackNumbers

		return {}

	def set_callback_number(self, callbacknumber):
		"""
		Set the number that grandcental calls
		@param callbacknumber should be a proper 10 digit number
		"""
		self._callbackNumber = callbacknumber
		callbackPostData = urllib.urlencode({
			'a_t': self._accessToken,
			'default_number': callbacknumber
		})
		try:
			callbackSetPage = self._browser.download(self._setforwardURL, callbackPostData)
		except urllib2.URLError, e:
			warnings.warn(traceback.format_exc())
			raise RuntimeError("%s is not accesible" % self._setforwardURL)

		self._browser.cookies.save()
		return True

	def get_callback_number(self):
		"""
		@returns Current callback number or None
		"""
		for c in self._browser.cookies:
			if c.name == "pda_forwarding_number":
				return c.value
		return self._callbackNumber

	def get_recent(self):
		"""
		@returns Iterable of (personsName, phoneNumber, date, action)
		"""
		try:
			recentCallsPage = self._browser.download(self._inboxallURL)
		except urllib2.URLError, e:
			warnings.warn(traceback.format_exc())
			raise RuntimeError("%s is not accesible" % self._inboxallURL)

		for match in self._inboxRe.finditer(recentCallsPage):
			phoneNumber = match.group(4)
			action = saxutils.unescape(match.group(1))
			date = saxutils.unescape(match.group(2))
			personsName = saxutils.unescape(match.group(3))
			yield personsName, phoneNumber, date, action

	def get_addressbooks(self):
		"""
		@returns Iterable of (Address Book Factory, Book Id, Book Name)
		"""
		yield self, "", ""

	def open_addressbook(self, bookId):
		return self

	@staticmethod
	def contact_source_short_name(contactId):
		return "GC"

	@staticmethod
	def factory_name():
		return "Grand Central"

	def get_contacts(self):
		"""
		@returns Iterable of (contact id, contact name)
		"""
		if self.__contacts is None:
			self.__contacts = []

			contactsPagesUrls = [self._contactsURL]
			for contactsPageUrl in contactsPagesUrls:
				try:
					contactsPage = self._browser.download(contactsPageUrl)
				except urllib2.URLError, e:
					warnings.warn(traceback.format_exc())
					raise RuntimeError("%s is not accesible" % contactsPageUrl)
				for contact_match in self._contactsRe.finditer(contactsPage):
					contactId = contact_match.group(1)
					contactName = contact_match.group(2)
					contact = contactId, saxutils.unescape(contactName)
					self.__contacts.append(contact)
					yield contact

				next_match = self._contactsNextRe.match(contactsPage)
				if next_match is not None:
					newContactsPageUrl = self._contactsURL + next_match.group(1)
					contactsPagesUrls.append(newContactsPageUrl)
		else:
			for contact in self.__contacts:
				yield contact

	def get_contact_details(self, contactId):
		"""
		@returns Iterable of (Phone Type, Phone Number)
		"""
		try:
			detailPage = self._browser.download(self._contactDetailURL + '/' + contactId)
		except urllib2.URLError, e:
			warnings.warn(traceback.format_exc())
			raise RuntimeError("%s is not accesible" % self._contactDetailURL)

		for detail_match in self._contactDetailPhoneRe.finditer(detailPage):
			phoneType = saxutils.unescape(detail_match.group(1))
			phoneNumber = detail_match.group(2)
			yield (phoneType, phoneNumber)

	def get_messages(self):
		return ()

	def _grab_token(self, data):
		"Pull the magic cookie from the datastream"
		atGroup = self._accessTokenRe.search(data)
		if atGroup is None:
			raise RuntimeError("Could not extract authentication token from GrandCentral")
		self._accessToken = atGroup.group(1)

		anGroup = self._accountNumRe.search(data)
		if anGroup is not None:
			self._accountNum = anGroup.group(1)
		else:
			warnings.warn("Could not extract account number from GrandCentral", UserWarning, 2)

		self._callbackNumbers = {}
		for match in self._callbackRe.finditer(data):
			self._callbackNumbers[match.group(1)] = match.group(2)


def test_backend(username, password):
	import pprint
	backend = GCDialer()
	print "Authenticated: ", backend.is_authed()
	print "Login?: ", backend.login(username, password)
	print "Authenticated: ", backend.is_authed()
	# print "Token: ", backend._accessToken
	print "Account: ", backend.get_account_number()
	print "Callback: ", backend.get_callback_number()
	# print "All Callback: ",
	# pprint.pprint(backend.get_callback_numbers())
	# print "Recent: ",
	# pprint.pprint(list(backend.get_recent()))
	# print "Contacts: ",
	# for contact in backend.get_contacts():
	#	print contact
	#	pprint.pprint(list(backend.get_contact_details(contact[0])))

	return backend
