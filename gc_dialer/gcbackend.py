#!/usr/bin/python

"""
Grandcentral Dialer backend code
Eric Warnke <ericew@gmail.com>
Copyright 2008 GPLv2
"""


import os
import re
import urllib
import urllib2
import time
import warnings

from browser_emu import MozillaEmulator


class GCDialer(object):
	"""
	This class encapsulates all of the knowledge necessary to interace with the grandcentral servers
	the functions include login, setting up a callback number, and initalting a callback
	"""

	_gcDialingStrRe = re.compile("This may take a few seconds", re.M) # string from Grandcentral.com on successful dial
	_accessTokenRe = re.compile(r"""<input type="hidden" name="a_t" [^>]*value="(.*)"/>""")
	_isLoginPageRe = re.compile(r"""<form method="post" action="https://www.grandcentral.com/mobile/account/login">""")
	_callbackRe = re.compile(r"""name="default_number" value="(\d+)" />\s+(.*)\s$""", re.M)
	_accountNumRe = re.compile(r"""<img src="/images/mobile/inbox_logo.gif" alt="GrandCentral" />\s*(.{14})\s*&nbsp""", re.M)
	_inboxRe = re.compile(r"""<td>.*?(voicemail|received|missed|call return).*?</td>\s+<td>\s+<font size="2">\s+(.*?)\s+&nbsp;\|&nbsp;\s+<a href="/mobile/contacts/.*?">(.*?)\s?</a>\s+<br/>\s+(.*?)\s?<a href=""", re.S)
	_contactsRe = re.compile(r"""<a href="/mobile/contacts/detail/(\d+)">(.*?)</a>""", re.S)
	_contactsNextRe = re.compile(r""".*<a href="/mobile/contacts(\?page=\d+)">Next</a>""", re.S)
	_contactDetailGroupRe	= re.compile(r"""Group:\s*(\w*)""", re.S)
	_contactDetailPhoneRe	= re.compile(r"""(\w+):[0-9\-\(\) \t]*?<a href="/mobile/calls/click_to_call\?destno=(\d+).*?">call</a>""", re.S)

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
		self._msg = ""

		self._browser = MozillaEmulator(None, 0)
		if cookieFile is None:
			cookieFile = os.path.join(os.path.expanduser("~"), ".gc_dialer_cookies.txt")
		self._browser.cookies.filename = cookieFile
		if os.path.isfile(cookieFile):
			self._browser.cookies.load()

		self._accessToken = None
		self._accountNum = None
		self._callbackNumbers = {}
		self._lastAuthed = 0.0

	def is_authed(self, force = False):
		"""
		Attempts to detect a current session and pull the auth token ( a_t ) from the page.
		@note Once logged in try not to reauth more than once a minute.
		@returns If authenticated
		"""

		if time.time() - self._lastAuthed < 60 and not force:
			return True

		try:
			forwardSelectionPage = self._browser.download(GCDialer._forwardselectURL)
		except urllib2.URLError, e:
			warnings.warn("%s is not accesible" % GCDialer._forwardselectURL, UserWarning, 2)
			return False

		self._browser.cookies.save()
		if GCDialer._isLoginPageRe.search(forwardSelectionPage) is None:
			self._grab_token(forwardSelectionPage)
			self._lastAuthed = time.time()
			return True

		return False

	def login(self, username, password):
		"""
		Attempt to login to grandcentral
		@returns Whether login was successful or not
		"""
		if self.is_authed():
			return True

		loginPostData = urllib.urlencode( {'username' : username , 'password' : password } )

		try:
			loginSuccessOrFailurePage = self._browser.download(GCDialer._loginURL, loginPostData)
		except urllib2.URLError, e:
			warnings.warn("%s is not accesible" % GCDialer._loginURL, UserWarning, 2)
			return False

		return self.is_authed()

	def dial(self, number):
		"""
		This is the main function responsible for initating the callback
		"""
		self._msg = ""

		# If the number is not valid throw exception
		if not self.is_valid_syntax(number):
			raise ValueError('number is not valid')

		# No point if we don't have the magic cookie
		if not self.is_authed():
			self._msg = "Not authenticated"
			return False

		# Strip leading 1 from 11 digit dialing
		if len(number) == 11 and number[0] == 1:
			number = number[1:]

		try:
			callSuccessPage = self._browser.download(
				GCDialer._clicktocallURL % (self._accessToken, number),
				None,
				{'Referer' : 'http://www.grandcentral.com/mobile/messages'}
			)
		except urllib2.URLError, e:
			warnings.warn("%s is not accesible" % GCDialer._clicktocallURL, UserWarning, 2)
			return False

		if GCDialer._gcDialingStrRe.search(callSuccessPage) is not None:
			return True
		else:
			self._msg = "Grand Central returned an error"
			return False

		self._msg = "Unknown Error"
		return False

	def clear_caches(self):
		pass

	def reset(self):
		self._lastAuthed = 0.0
		self._browser.cookies.clear()
		self._browser.cookies.save()

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
			if not re.compile(r"""1747""").match(number) is None:
				self.set_callback_number(number)
				return

		for number, description in numbers.iteritems():
			if not re.compile(r"""gizmo""", re.I).search(description) is None:
				self.set_callback_number(number)
				return

		for number, description in numbers.iteritems():
			if not re.compile(r"""computer""", re.I).search(description) is None:
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
		callbackPostData = urllib.urlencode({'a_t' : self._accessToken, 'default_number' : callbacknumber })
		try:
			callbackSetPage = self._browser.download(GCDialer._setforwardURL, callbackPostData)
		except urllib2.URLError, e:
			warnings.warn("%s is not accesible" % GCDialer._setforwardURL, UserWarning, 2)
			return False

		self._browser.cookies.save()
		return True

	def get_callback_number(self):
		"""
		@returns Current callback number or None
		"""
		for c in self._browser.cookies:
			if c.name == "pda_forwarding_number":
				return c.value
		return None

	def get_recent(self):
		"""
		@returns Iterable of (personsName, phoneNumber, date, action)
		"""
		try:
			recentCallsPage = self._browser.download(GCDialer._inboxallURL)
		except urllib2.URLError, e:
			warnings.warn("%s is not accesible" % GCDialer._inboxallURL, UserWarning, 2)
			return

		for match in self._inboxRe.finditer(recentCallsPage):
			phoneNumber = match.group(4)
			action = match.group(1)
			date = match.group(2)
			personsName = match.group(3)
			yield personsName, phoneNumber, date, action

	def get_contacts(self):
		contactsPagesUrls = [GCDialer._contactsURL]
		for contactsPageUrl in contactsPagesUrls:
			print contactsPageUrl
			contactsPage = self._browser.download(contactsPageUrl)
			for contact_match in self._contactsRe.finditer(contactsPage):
				contactId = contact_match.group(1)
				contactName = contact_match.group(2)
				yield contactId, contactName
			next_match = self._contactsNextRe.match(contactsPage)
			if next_match is not None:
				newContactsPageUrl = self._contactsURL + next_match.group(1)
				contactsPagesUrls.append(newContactsPageUrl)
	
	def get_contact_details(self, contactId):
		detailPage = self._browser.download(GCDialer._contactDetailURL + '/' + contactId)
		for detail_match in self._contactDetailPhoneRe.finditer(detailPage):
			phoneType = detail_match.group(1)
			phoneNumber = detail_match.group(2)
			yield (phoneType, phoneNumber)

	def _grab_token(self, data):
		"Pull the magic cookie from the datastream"
		atGroup = GCDialer._accessTokenRe.search(data)
		self._accessToken = atGroup.group(1)

		anGroup = GCDialer._accountNumRe.search(data)
		self._accountNum = anGroup.group(1)

		self._callbackNumbers = {}
		for match in GCDialer._callbackRe.finditer(data):
			self._callbackNumbers[match.group(1)] = match.group(2)
