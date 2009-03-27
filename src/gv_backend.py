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
Google Voice backend code

Resources
	http://thatsmith.com/2009/03/google-voice-addon-for-firefox/
	http://posttopic.com/topic/google-voice-add-on-development
"""


import os
import re
import urllib
import urllib2
import time
import warnings
import traceback

from xml.etree import ElementTree

from browser_emu import MozillaEmulator

try:
	import simplejson
except ImportError:
	simplejson = None


_TRUE_REGEX = re.compile("true")
_FALSE_REGEX = re.compile("false")


def safe_eval(s):
	s = _TRUE_REGEX.sub("True", s)
	s = _FALSE_REGEX.sub("False", s)
	return eval(s, {}, {})


if simplejson is None:
	def parse_json(flattened):
		return safe_eval(flattened)
else:
	def parse_json(flattened):
		return simplejson.loads(flattened)


class GVDialer(object):
	"""
	This class encapsulates all of the knowledge necessary to interace with the grandcentral servers
	the functions include login, setting up a callback number, and initalting a callback
	"""

	_tokenRe = re.compile(r"""<input.*?name="_rnr_se".*?value="(.*?)"\s*/>""")
	_accountNumRe = re.compile(r"""<b class="ms2">(.{14})</b></div>""")
	_callbackRe = re.compile(r"""\s+(.*?):\s*(.*?)<br\s*/>\s*$""", re.M)
	_validateRe = re.compile("^[0-9]{10,}$")
	_gvDialingStrRe = re.compile("This may take a few seconds", re.M)

	_contactsRe = re.compile(r"""<a href="/voice/m/contact/(\d+)">(.*?)</a>""", re.S)
	_contactsNextRe = re.compile(r""".*<a href="/voice/m/contacts(\?p=\d+)">Next.*?</a>""", re.S)
	_contactDetailPhoneRe = re.compile(r"""<div.*?>([0-9\-\(\) \t]+?)<span.*?>\((\w+)\)</span>""", re.S)

	_clicktocallURL = "https://www.google.com/voice/m/sendcall"
	_contactsURL = "https://www.google.com/voice/mobile/contacts"
	_contactDetailURL = "https://www.google.com/voice/mobile/contact"

	_loginURL = "https://www.google.com/accounts/ServiceLoginAuth"
	_setforwardURL = "https://www.google.com//voice/m/setphone"
	_accountNumberURL = "https://www.google.com/voice/mobile"
	_forwardURL = "https://www.google.com/voice/mobile/phones"

	_recentCallsURL = "https://www.google.com/voice/inbox/recent/"
	_placedCallsURL = "https://www.google.com/voice/inbox/recent/placed/"
	_receivedCallsURL = "https://www.google.com/voice/inbox/recent/received/"
	_missedCallsURL = "https://www.google.com/voice/inbox/recent/missed/"

	def __init__(self, cookieFile = None):
		# Important items in this function are the setup of the browser emulation and cookie file
		self._browser = MozillaEmulator(None, 0)
		if cookieFile is None:
			cookieFile = os.path.join(os.path.expanduser("~"), ".gv_cookies.txt")
		self._browser.cookies.filename = cookieFile
		if os.path.isfile(cookieFile):
			self._browser.cookies.load()

		self._token = ""
		self._accountNum = None
		self._lastAuthed = 0.0
		self._callbackNumber = ""
		self._callbackNumbers = {}

		self.__contacts = None

	def is_authed(self, force = False):
		"""
		Attempts to detect a current session
		@note Once logged in try not to reauth more than once a minute.
		@returns If authenticated
		"""

		if (time.time() - self._lastAuthed) < 60 and not force:
			return True

		try:
			self._grab_account_info()
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

		loginPostData = urllib.urlencode({
			'Email' : username,
			'Passwd' : password,
			'service': "grandcentral",
			"ltmpl": "mobile",
			"btmpl": "mobile",
			"PersistentCookie": "yes",
		})

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
			clickToCallData = urllib.urlencode({
				"number": number,
				"phone": self._callbackNumber,
				"_rnr_se": self._token,
			})
			otherData = {
				'Referer' : 'https://google.com/voice/m/callsms',
			}
			callSuccessPage = self._browser.download(self._clicktocallURL, clickToCallData, None, otherData)
		except urllib2.URLError, e:
			warnings.warn(traceback.format_exc())
			raise RuntimeError("%s is not accesible" % self._clicktocallURL)

		if self._gvDialingStrRe.search(callSuccessPage) is None:
			raise RuntimeError("Google Voice returned an error")

		return True

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
			'_rnr_se': self._token,
			'phone': callbacknumber
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
		return self._callbackNumber

	def get_recent(self):
		"""
		@returns Iterable of (personsName, phoneNumber, date, action)
		"""
		for url in (
			self._receivedCallsURL,
			self._missedCallsURL,
			self._placedCallsURL,
		):
			try:
				allRecentData = self._grab_json(url)
			except urllib2.URLError, e:
				warnings.warn(traceback.format_exc())
				raise RuntimeError("%s is not accesible" % self._clicktocallURL)

			for recentCallData in allRecentData["messages"].itervalues():
				number = recentCallData["displayNumber"]
				date = recentCallData["relativeStartTime"]
				action = ", ".join((
					label.title()
					for label in recentCallData["labels"]
						if label.lower() != "all" and label.lower() != "inbox"
				))
				yield "", number, date, action

	def get_addressbooks(self):
		"""
		@returns Iterable of (Address Book Factory, Book Id, Book Name)
		"""
		yield self, "", ""

	def open_addressbook(self, bookId):
		return self

	@staticmethod
	def contact_source_short_name(contactId):
		return "GV"

	@staticmethod
	def factory_name():
		return "Google Voice"

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
					raise RuntimeError("%s is not accesible" % self._clicktocallURL)
				for contact_match in self._contactsRe.finditer(contactsPage):
					contactId = contact_match.group(1)
					contactName = contact_match.group(2)
					contact = contactId, contactName
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
			raise RuntimeError("%s is not accesible" % self._clicktocallURL)

		for detail_match in self._contactDetailPhoneRe.finditer(detailPage):
			phoneNumber = detail_match.group(1)
			phoneType = detail_match.group(2)
			yield (phoneType, phoneNumber)

	def _grab_json(self, url):
		flatXml = self._browser.download(url)
		xmlTree = ElementTree.fromstring(flatXml)
		jsonElement = xmlTree.getchildren()[0]
		flatJson = jsonElement.text
		jsonTree = parse_json(flatJson)
		return jsonTree

	def _grab_account_info(self):
		page = self._browser.download(self._forwardURL)

		tokenGroup = self._tokenRe.search(page)
		if tokenGroup is None:
			raise RuntimeError("Could not extract authentication token from GoogleVoice")
		self._token = tokenGroup.group(1)

		anGroup = self._accountNumRe.search(page)
		if anGroup is None:
			raise RuntimeError("Could not extract account number from GoogleVoice")
		self._accountNum = anGroup.group(1)

		self._callbackNumbers = {}
		for match in self._callbackRe.finditer(page):
			callbackNumber = match.group(2)
			callbackName = match.group(1)
			self._callbackNumbers[callbackNumber] = callbackName


def test_backend(username, password):
	import pprint
	backend = GVDialer()
	print "Authenticated: ", backend.is_authed()
	print "Login?: ", backend.login(username, password)
	print "Authenticated: ", backend.is_authed()
	print "Token: ", backend._token
	print "Account: ", backend.get_account_number()
	print "Callback: ", backend.get_callback_number()
	print "All Callback: ",
	pprint.pprint(backend.get_callback_numbers())
	# print "Recent: ",
	# pprint.pprint(list(backend.get_recent()))
	# print "Contacts: ",
	# for contact in backend.get_contacts():
	#	print contact
	#	pprint.pprint(list(backend.get_contact_details(contact[0])))

	return backend
