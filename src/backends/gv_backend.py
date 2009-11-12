#!/usr/bin/python

"""
DialCentral - Front end for Google's GoogleVoice service.
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

Google Voice backend code

Resources
	http://thatsmith.com/2009/03/google-voice-addon-for-firefox/
	http://posttopic.com/topic/google-voice-add-on-development
"""

from __future__ import with_statement

import os
import re
import urllib
import urllib2
import time
import datetime
import itertools
import logging
from xml.sax import saxutils

from xml.etree import ElementTree

try:
	import simplejson
except ImportError:
	simplejson = None

import browser_emu


_moduleLogger = logging.getLogger("gvoice.dialer")


def safe_eval(s):
	_TRUE_REGEX = re.compile("true")
	_FALSE_REGEX = re.compile("false")
	s = _TRUE_REGEX.sub("True", s)
	s = _FALSE_REGEX.sub("False", s)
	return eval(s, {}, {})


if simplejson is None:
	def parse_json(flattened):
		return safe_eval(flattened)
else:
	def parse_json(flattened):
		return simplejson.loads(flattened)


def itergroup(iterator, count, padValue = None):
	"""
	Iterate in groups of 'count' values. If there
	aren't enough values, the last result is padded with
	None.

	>>> for val in itergroup([1, 2, 3, 4, 5, 6], 3):
	... 	print tuple(val)
	(1, 2, 3)
	(4, 5, 6)
	>>> for val in itergroup([1, 2, 3, 4, 5, 6], 3):
	... 	print list(val)
	[1, 2, 3]
	[4, 5, 6]
	>>> for val in itergroup([1, 2, 3, 4, 5, 6, 7], 3):
	... 	print tuple(val)
	(1, 2, 3)
	(4, 5, 6)
	(7, None, None)
	>>> for val in itergroup("123456", 3):
	... 	print tuple(val)
	('1', '2', '3')
	('4', '5', '6')
	>>> for val in itergroup("123456", 3):
	... 	print repr("".join(val))
	'123'
	'456'
	"""
	paddedIterator = itertools.chain(iterator, itertools.repeat(padValue, count-1))
	nIterators = (paddedIterator, ) * count
	return itertools.izip(*nIterators)


class NetworkError(RuntimeError):
	pass


class GVDialer(object):
	"""
	This class encapsulates all of the knowledge necessary to interact with the GoogleVoice servers
	the functions include login, setting up a callback number, and initalting a callback
	"""

	def __init__(self, cookieFile = None):
		# Important items in this function are the setup of the browser emulation and cookie file
		self._browser = browser_emu.MozillaEmulator(1)
		if cookieFile is None:
			cookieFile = os.path.join(os.path.expanduser("~"), ".gv_cookies.txt")
		self._browser.cookies.filename = cookieFile
		if os.path.isfile(cookieFile):
			self._browser.cookies.load()

		self._token = ""
		self._accountNum = ""
		self._lastAuthed = 0.0
		self._callbackNumber = ""
		self._callbackNumbers = {}

		# Suprisingly, moving all of these from class to self sped up startup time

		self._validateRe = re.compile("^[0-9]{10,}$")

		self._forwardURL = "https://www.google.com/voice/mobile/phones"
		self._tokenURL = "http://www.google.com/voice/m"
		self._loginURL = "https://www.google.com/accounts/ServiceLoginAuth"
		self._galxRe = re.compile(r"""<input.*?name="GALX".*?value="(.*?)".*?/>""", re.MULTILINE | re.DOTALL)
		self._tokenRe = re.compile(r"""<input.*?name="_rnr_se".*?value="(.*?)"\s*/>""")
		self._accountNumRe = re.compile(r"""<b class="ms\d">(.{14})</b></div>""")
		self._callbackRe = re.compile(r"""\s+(.*?):\s*(.*?)<br\s*/>\s*$""", re.M)

		self._gvDialingStrRe = re.compile("This may take a few seconds", re.M)
		self._clicktocallURL = "https://www.google.com/voice/m/sendcall"
		self._sendSmsURL = "https://www.google.com/voice/m/sendsms"

		self._recentCallsURL = "https://www.google.com/voice/inbox/recent/"
		self._placedCallsURL = "https://www.google.com/voice/inbox/recent/placed/"
		self._receivedCallsURL = "https://www.google.com/voice/inbox/recent/received/"
		self._missedCallsURL = "https://www.google.com/voice/inbox/recent/missed/"

		self._contactsRe = re.compile(r"""<a href="/voice/m/contact/(\d+)">(.*?)</a>""", re.S)
		self._contactsNextRe = re.compile(r""".*<a href="/voice/m/contacts(\?p=\d+)">Next.*?</a>""", re.S)
		self._contactsURL = "https://www.google.com/voice/mobile/contacts"
		self._contactDetailPhoneRe = re.compile(r"""<div.*?>([0-9+\-\(\) \t]+?)<span.*?>\((\w+)\)</span>""", re.S)
		self._contactDetailURL = "https://www.google.com/voice/mobile/contact"

		self._voicemailURL = "https://www.google.com/voice/inbox/recent/voicemail/"
		self._smsURL = "https://www.google.com/voice/inbox/recent/sms/"
		self._seperateVoicemailsRegex = re.compile(r"""^\s*<div id="(\w+)"\s* class=".*?gc-message.*?">""", re.MULTILINE | re.DOTALL)
		self._exactVoicemailTimeRegex = re.compile(r"""<span class="gc-message-time">(.*?)</span>""", re.MULTILINE)
		self._relativeVoicemailTimeRegex = re.compile(r"""<span class="gc-message-relative">(.*?)</span>""", re.MULTILINE)
		self._voicemailNameRegex = re.compile(r"""<a class=.*?gc-message-name-link.*?>(.*?)</a>""", re.MULTILINE | re.DOTALL)
		self._voicemailNumberRegex = re.compile(r"""<input type="hidden" class="gc-text gc-quickcall-ac" value="(.*?)"/>""", re.MULTILINE)
		self._prettyVoicemailNumberRegex = re.compile(r"""<span class="gc-message-type">(.*?)</span>""", re.MULTILINE)
		self._voicemailLocationRegex = re.compile(r"""<span class="gc-message-location">.*?<a.*?>(.*?)</a></span>""", re.MULTILINE)
		self._messagesContactID = re.compile(r"""<a class=".*?gc-message-name-link.*?">.*?</a>\s*?<span .*?>(.*?)</span>""", re.MULTILINE)
		self._voicemailMessageRegex = re.compile(r"""(<span id="\d+-\d+" class="gc-word-(.*?)">(.*?)</span>|<a .*? class="gc-message-mni">(.*?)</a>)""", re.MULTILINE)
		self._smsFromRegex = re.compile(r"""<span class="gc-message-sms-from">(.*?)</span>""", re.MULTILINE | re.DOTALL)
		self._smsTimeRegex = re.compile(r"""<span class="gc-message-sms-time">(.*?)</span>""", re.MULTILINE | re.DOTALL)
		self._smsTextRegex = re.compile(r"""<span class="gc-message-sms-text">(.*?)</span>""", re.MULTILINE | re.DOTALL)

	def is_authed(self, force = False):
		"""
		Attempts to detect a current session
		@note Once logged in try not to reauth more than once a minute.
		@returns If authenticated
		"""
		if (time.time() - self._lastAuthed) < 120 and not force:
			return True

		try:
			page = self._browser.download(self._forwardURL)
			self._grab_account_info(page)
		except Exception, e:
			_moduleLogger.exception(str(e))
			return False

		self._browser.cookies.save()
		self._lastAuthed = time.time()
		return True

	def _get_token(self):
		try:
			tokenPage = self._browser.download(self._tokenURL)
		except urllib2.URLError, e:
			_moduleLogger.exception("Translating error: %s" % str(e))
			raise NetworkError("%s is not accesible" % self._loginURL)
		galxTokens = self._galxRe.search(tokenPage)
		if galxTokens is not None:
			galxToken = galxTokens.group(1)
		else:
			galxToken = ""
			_moduleLogger.debug("Could not grab GALX token")
		return galxToken

	def _login(self, username, password, token):
		loginPostData = urllib.urlencode({
			'Email' : username,
			'Passwd' : password,
			'service': "grandcentral",
			"ltmpl": "mobile",
			"btmpl": "mobile",
			"PersistentCookie": "yes",
			"GALX": token,
			"continue": self._forwardURL,
		})

		try:
			loginSuccessOrFailurePage = self._browser.download(self._loginURL, loginPostData)
		except urllib2.URLError, e:
			_moduleLogger.exception("Translating error: %s" % str(e))
			raise NetworkError("%s is not accesible" % self._loginURL)
		return loginSuccessOrFailurePage

	def login(self, username, password):
		"""
		Attempt to login to GoogleVoice
		@returns Whether login was successful or not
		"""
		self.logout()
		galxToken = self._get_token()
		loginSuccessOrFailurePage = self._login(username, password, galxToken)

		try:
			self._grab_account_info(loginSuccessOrFailurePage)
		except Exception, e:
			# Retry in case the redirect failed
			# luckily is_authed does everything we need for a retry
			loggedIn = self.is_authed(True)
			if not loggedIn:
				_moduleLogger.exception(str(e))
				return False
			_moduleLogger.info("Redirection failed on initial login attempt, auto-corrected for this")

		self._browser.cookies.save()
		self._lastAuthed = time.time()
		return True

	def logout(self):
		self._lastAuthed = 0.0
		self._browser.cookies.clear()
		self._browser.cookies.save()

	def dial(self, number):
		"""
		This is the main function responsible for initating the callback
		"""
		number = self._send_validation(number)
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
			_moduleLogger.exception("Translating error: %s" % str(e))
			raise NetworkError("%s is not accesible" % self._clicktocallURL)

		if self._gvDialingStrRe.search(callSuccessPage) is None:
			raise RuntimeError("Google Voice returned an error")

		return True

	def send_sms(self, number, message):
		number = self._send_validation(number)
		try:
			smsData = urllib.urlencode({
				"number": number,
				"smstext": message,
				"_rnr_se": self._token,
				"id": "undefined",
				"c": "undefined",
			})
			otherData = {
				'Referer' : 'https://google.com/voice/m/sms',
			}
			smsSuccessPage = self._browser.download(self._sendSmsURL, smsData, None, otherData)
		except urllib2.URLError, e:
			_moduleLogger.exception("Translating error: %s" % str(e))
			raise NetworkError("%s is not accesible" % self._sendSmsURL)

		return True

	def is_valid_syntax(self, number):
		"""
		@returns If This number be called ( syntax validation only )
		"""
		return self._validateRe.match(number) is not None

	def get_account_number(self):
		"""
		@returns The GoogleVoice phone number
		"""
		return self._accountNum

	def get_callback_numbers(self):
		"""
		@returns a dictionary mapping call back numbers to descriptions
		@note These results are cached for 30 minutes.
		"""
		if not self.is_authed():
			return {}
		return self._callbackNumbers

	def set_callback_number(self, callbacknumber):
		"""
		Set the number that GoogleVoice calls
		@param callbacknumber should be a proper 10 digit number
		"""
		self._callbackNumber = callbacknumber
		return True

	def get_callback_number(self):
		"""
		@returns Current callback number or None
		"""
		return self._callbackNumber

	def get_recent(self):
		"""
		@returns Iterable of (personsName, phoneNumber, exact date, relative date, action)
		"""
		for action, url in (
			("Received", self._receivedCallsURL),
			("Missed", self._missedCallsURL),
			("Placed", self._placedCallsURL),
		):
			try:
				flatXml = self._browser.download(url)
			except urllib2.URLError, e:
				_moduleLogger.exception("Translating error: %s" % str(e))
				raise NetworkError("%s is not accesible" % url)

			allRecentHtml = self._grab_html(flatXml)
			allRecentData = self._parse_voicemail(allRecentHtml)
			for recentCallData in allRecentData:
				recentCallData["action"] = action
				yield recentCallData

	def get_contacts(self):
		"""
		@returns Iterable of (contact id, contact name)
		"""
		contactsPagesUrls = [self._contactsURL]
		for contactsPageUrl in contactsPagesUrls:
			try:
				contactsPage = self._browser.download(contactsPageUrl)
			except urllib2.URLError, e:
				_moduleLogger.exception("Translating error: %s" % str(e))
				raise NetworkError("%s is not accesible" % contactsPageUrl)
			for contact_match in self._contactsRe.finditer(contactsPage):
				contactId = contact_match.group(1)
				contactName = saxutils.unescape(contact_match.group(2))
				contact = contactId, contactName
				yield contact

			next_match = self._contactsNextRe.match(contactsPage)
			if next_match is not None:
				newContactsPageUrl = self._contactsURL + next_match.group(1)
				contactsPagesUrls.append(newContactsPageUrl)

	def get_contact_details(self, contactId):
		"""
		@returns Iterable of (Phone Type, Phone Number)
		"""
		try:
			detailPage = self._browser.download(self._contactDetailURL + '/' + contactId)
		except urllib2.URLError, e:
			_moduleLogger.exception("Translating error: %s" % str(e))
			raise NetworkError("%s is not accesible" % self._contactDetailURL)

		for detail_match in self._contactDetailPhoneRe.finditer(detailPage):
			phoneNumber = detail_match.group(1)
			phoneType = saxutils.unescape(detail_match.group(2))
			yield (phoneType, phoneNumber)

	def get_messages(self):
		try:
			voicemailPage = self._browser.download(self._voicemailURL)
		except urllib2.URLError, e:
			_moduleLogger.exception("Translating error: %s" % str(e))
			raise NetworkError("%s is not accesible" % self._voicemailURL)
		voicemailHtml = self._grab_html(voicemailPage)
		voicemailJson = self._grab_json(voicemailPage)
		parsedVoicemail = self._parse_voicemail(voicemailHtml)
		voicemails = self._merge_messages(parsedVoicemail, voicemailJson)
		decoratedVoicemails = self._decorate_voicemail(voicemails)

		try:
			smsPage = self._browser.download(self._smsURL)
		except urllib2.URLError, e:
			_moduleLogger.exception("Translating error: %s" % str(e))
			raise NetworkError("%s is not accesible" % self._smsURL)
		smsHtml = self._grab_html(smsPage)
		smsJson = self._grab_json(smsPage)
		parsedSms = self._parse_sms(smsHtml)
		smss = self._merge_messages(parsedSms, smsJson)
		decoratedSms = self._decorate_sms(smss)

		allMessages = itertools.chain(decoratedVoicemails, decoratedSms)
		return allMessages

	def clear_caches(self):
		pass

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

	def _grab_json(self, flatXml):
		xmlTree = ElementTree.fromstring(flatXml)
		jsonElement = xmlTree.getchildren()[0]
		flatJson = jsonElement.text
		jsonTree = parse_json(flatJson)
		return jsonTree

	def _grab_html(self, flatXml):
		xmlTree = ElementTree.fromstring(flatXml)
		htmlElement = xmlTree.getchildren()[1]
		flatHtml = htmlElement.text
		return flatHtml

	def _grab_account_info(self, page):
		tokenGroup = self._tokenRe.search(page)
		if tokenGroup is None:
			raise RuntimeError("Could not extract authentication token from GoogleVoice")
		self._token = tokenGroup.group(1)

		anGroup = self._accountNumRe.search(page)
		if anGroup is not None:
			self._accountNum = anGroup.group(1)
		else:
			_moduleLogger.debug("Could not extract account number from GoogleVoice")

		self._callbackNumbers = {}
		for match in self._callbackRe.finditer(page):
			callbackNumber = match.group(2)
			callbackName = match.group(1)
			self._callbackNumbers[callbackNumber] = callbackName
		if len(self._callbackNumbers) == 0:
			_moduleLogger.debug("Could not extract callback numbers from GoogleVoice (the troublesome page follows):\n%s" % page)

	def _send_validation(self, number):
		if not self.is_valid_syntax(number):
			raise ValueError('Number is not valid: "%s"' % number)
		elif not self.is_authed():
			raise RuntimeError("Not Authenticated")

		if len(number) == 11 and number[0] == 1:
			# Strip leading 1 from 11 digit dialing
			number = number[1:]
		return number

	@staticmethod
	def _interpret_voicemail_regex(group):
		quality, content, number = group.group(2), group.group(3), group.group(4)
		if quality is not None and content is not None:
			return quality, content
		elif number is not None:
			return "high", number

	def _parse_voicemail(self, voicemailHtml):
		splitVoicemail = self._seperateVoicemailsRegex.split(voicemailHtml)
		for messageId, messageHtml in itergroup(splitVoicemail[1:], 2):
			exactTimeGroup = self._exactVoicemailTimeRegex.search(messageHtml)
			exactTime = exactTimeGroup.group(1).strip() if exactTimeGroup else ""
			exactTime = datetime.datetime.strptime(exactTime, "%m/%d/%y %I:%M %p")
			relativeTimeGroup = self._relativeVoicemailTimeRegex.search(messageHtml)
			relativeTime = relativeTimeGroup.group(1).strip() if relativeTimeGroup else ""
			locationGroup = self._voicemailLocationRegex.search(messageHtml)
			location = locationGroup.group(1).strip() if locationGroup else ""

			nameGroup = self._voicemailNameRegex.search(messageHtml)
			name = nameGroup.group(1).strip() if nameGroup else ""
			numberGroup = self._voicemailNumberRegex.search(messageHtml)
			number = numberGroup.group(1).strip() if numberGroup else ""
			prettyNumberGroup = self._prettyVoicemailNumberRegex.search(messageHtml)
			prettyNumber = prettyNumberGroup.group(1).strip() if prettyNumberGroup else ""
			contactIdGroup = self._messagesContactID.search(messageHtml)
			contactId = contactIdGroup.group(1).strip() if contactIdGroup else ""

			messageGroups = self._voicemailMessageRegex.finditer(messageHtml)
			messageParts = (
				self._interpret_voicemail_regex(group)
				for group in messageGroups
			) if messageGroups else ()

			yield {
				"id": messageId.strip(),
				"contactId": contactId,
				"name": name,
				"time": exactTime,
				"relTime": relativeTime,
				"prettyNumber": prettyNumber,
				"number": number,
				"location": location,
				"messageParts": messageParts,
				"type": "Voicemail",
			}

	def _decorate_voicemail(self, parsedVoicemails):
		messagePartFormat = {
			"med1": "<i>%s</i>",
			"med2": "%s",
			"high": "<b>%s</b>",
		}
		for voicemailData in parsedVoicemails:
			message = " ".join((
				messagePartFormat[quality] % part
				for (quality, part) in voicemailData["messageParts"]
			)).strip()
			if not message:
				message = "No Transcription"
			whoFrom = voicemailData["name"]
			when = voicemailData["time"]
			voicemailData["messageParts"] = ((whoFrom, message, when), )
			yield voicemailData

	def _parse_sms(self, smsHtml):
		splitSms = self._seperateVoicemailsRegex.split(smsHtml)
		for messageId, messageHtml in itergroup(splitSms[1:], 2):
			exactTimeGroup = self._exactVoicemailTimeRegex.search(messageHtml)
			exactTime = exactTimeGroup.group(1).strip() if exactTimeGroup else ""
			exactTime = datetime.datetime.strptime(exactTime, "%m/%d/%y %I:%M %p")
			relativeTimeGroup = self._relativeVoicemailTimeRegex.search(messageHtml)
			relativeTime = relativeTimeGroup.group(1).strip() if relativeTimeGroup else ""

			nameGroup = self._voicemailNameRegex.search(messageHtml)
			name = nameGroup.group(1).strip() if nameGroup else ""
			numberGroup = self._voicemailNumberRegex.search(messageHtml)
			number = numberGroup.group(1).strip() if numberGroup else ""
			prettyNumberGroup = self._prettyVoicemailNumberRegex.search(messageHtml)
			prettyNumber = prettyNumberGroup.group(1).strip() if prettyNumberGroup else ""
			contactIdGroup = self._messagesContactID.search(messageHtml)
			contactId = contactIdGroup.group(1).strip() if contactIdGroup else ""

			fromGroups = self._smsFromRegex.finditer(messageHtml)
			fromParts = (group.group(1).strip() for group in fromGroups)
			textGroups = self._smsTextRegex.finditer(messageHtml)
			textParts = (group.group(1).strip() for group in textGroups)
			timeGroups = self._smsTimeRegex.finditer(messageHtml)
			timeParts = (group.group(1).strip() for group in timeGroups)

			messageParts = itertools.izip(fromParts, textParts, timeParts)

			yield {
				"id": messageId.strip(),
				"contactId": contactId,
				"name": name,
				"time": exactTime,
				"relTime": relativeTime,
				"prettyNumber": prettyNumber,
				"number": number,
				"location": "",
				"messageParts": messageParts,
				"type": "Texts",
			}

	def _decorate_sms(self, parsedTexts):
		return parsedTexts

	@staticmethod
	def _merge_messages(parsedMessages, json):
		for message in parsedMessages:
			id = message["id"]
			jsonItem = json["messages"][id]
			message["isRead"] = jsonItem["isRead"]
			message["isSpam"] = jsonItem["isSpam"]
			message["isTrash"] = jsonItem["isTrash"]
			message["isArchived"] = "inbox" not in jsonItem["labels"]
			yield message


def set_sane_callback(backend):
	"""
	Try to set a sane default callback number on these preferences
	1) 1747 numbers ( Gizmo )
	2) anything with gizmo in the name
	3) anything with computer in the name
	4) the first value
	"""
	numbers = backend.get_callback_numbers()

	priorityOrderedCriteria = [
		("1747", None),
		(None, "gizmo"),
		(None, "computer"),
		(None, "sip"),
		(None, None),
	]

	for numberCriteria, descriptionCriteria in priorityOrderedCriteria:
		for number, description in numbers.iteritems():
			if numberCriteria is not None and re.compile(numberCriteria).match(number) is None:
				continue
			if descriptionCriteria is not None and re.compile(descriptionCriteria).match(description) is None:
				continue
			backend.set_callback_number(number)
			return


def sort_messages(allMessages):
	sortableAllMessages = [
		(message["time"], message)
		for message in allMessages
	]
	sortableAllMessages.sort(reverse=True)
	return (
		message
		for (exactTime, message) in sortableAllMessages
	)


def decorate_recent(recentCallData):
	"""
	@returns (personsName, phoneNumber, date, action)
	"""
	contactId = recentCallData["contactId"]
	if recentCallData["name"]:
		header = recentCallData["name"]
	elif recentCallData["prettyNumber"]:
		header = recentCallData["prettyNumber"]
	elif recentCallData["location"]:
		header = recentCallData["location"]
	else:
		header = "Unknown"

	number = recentCallData["number"]
	relTime = recentCallData["relTime"]
	action = recentCallData["action"]
	return contactId, header, number, relTime, action


def decorate_message(messageData):
	contactId = messageData["contactId"]
	exactTime = messageData["time"]
	if messageData["name"]:
		header = messageData["name"]
	elif messageData["prettyNumber"]:
		header = messageData["prettyNumber"]
	else:
		header = "Unknown"
	number = messageData["number"]
	relativeTime = messageData["relTime"]

	messageParts = list(messageData["messageParts"])
	if len(messageParts) == 0:
		messages = ("No Transcription", )
	elif len(messageParts) == 1:
		messages = (messageParts[0][1], )
	else:
		messages = [
			"<b>%s</b>: %s" % (messagePart[0], messagePart[1])
			for messagePart in messageParts
		]

	decoratedResults = contactId, header, number, relativeTime, messages
	return decoratedResults


def test_backend(username, password):
	backend = GVDialer()
	print "Authenticated: ", backend.is_authed()
	if not backend.is_authed():
		print "Login?: ", backend.login(username, password)
	print "Authenticated: ", backend.is_authed()

	print "Token: ", backend._token
	#print "Account: ", backend.get_account_number()
	#print "Callback: ", backend.get_callback_number()
	#print "All Callback: ",
	import pprint
	#pprint.pprint(backend.get_callback_numbers())

	#print "Recent: "
	#for data in backend.get_recent():
	#	pprint.pprint(data)
	#for data in sort_messages(backend.get_recent()):
	#	pprint.pprint(decorate_recent(data))
	#pprint.pprint(list(backend.get_recent()))

	#print "Contacts: ",
	#for contact in backend.get_contacts():
	#	print contact
	#	pprint.pprint(list(backend.get_contact_details(contact[0])))

	print "Messages: ",
	for message in backend.get_messages():
		message["messageParts"] = list(message["messageParts"])
		pprint.pprint(message)
	#for message in sort_messages(backend.get_messages()):
	#	pprint.pprint(decorate_message(message))

	return backend


def grab_debug_info(username, password):
	cookieFile = os.path.join(".", "raw_cookies.txt")
	try:
		os.remove(cookieFile)
	except OSError:
		pass

	backend = GVDialer(cookieFile)
	browser = backend._browser

	_TEST_WEBPAGES = [
		("forward", backend._forwardURL),
		("token", backend._tokenURL),
		("login", backend._loginURL),
		("contacts", backend._contactsURL),

		("voicemail", backend._voicemailURL),
		("sms", backend._smsURL),

		("recent", backend._recentCallsURL),
		("placed", backend._placedCallsURL),
		("recieved", backend._receivedCallsURL),
		("missed", backend._missedCallsURL),
	]

	# Get Pages
	print "Grabbing pre-login pages"
	for name, url in _TEST_WEBPAGES:
		try:
			page = browser.download(url)
		except StandardError, e:
			print e.message
			continue
		print "\tWriting to file"
		with open("not_loggedin_%s.txt" % name, "w") as f:
			f.write(page)

	# Login
	print "Attempting login"
	galxToken = backend._get_token()
	loginSuccessOrFailurePage = backend._login(username, password, galxToken)
	with open("loggingin.txt", "w") as f:
		print "\tWriting to file"
		f.write(loginSuccessOrFailurePage)
	try:
		backend._grab_account_info(loginSuccessOrFailurePage)
	except Exception:
		# Retry in case the redirect failed
		# luckily is_authed does everything we need for a retry
		loggedIn = backend.is_authed(True)
		if not loggedIn:
			raise

	# Get Pages
	print "Grabbing post-login pages"
	for name, url in _TEST_WEBPAGES:
		try:
			page = browser.download(url)
		except StandardError, e:
			print e.message
			continue
		print "\tWriting to file"
		with open("loggedin_%s.txt" % name, "w") as f:
			f.write(page)

	# Cookies
	browser.cookies.save()
	print "\tWriting cookies to file"
	with open("cookies.txt", "w") as f:
		f.writelines(
			"%s: %s\n" % (c.name, c.value)
			for c in browser.cookies
		)


if __name__ == "__main__":
	import sys
	logging.basicConfig(level=logging.DEBUG)
	#test_backend(sys.argv[1], sys.argv[2])
	grab_debug_info(sys.argv[1], sys.argv[2])
