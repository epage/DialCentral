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
	import simplejson as _simplejson
	simplejson = _simplejson
except ImportError:
	simplejson = None

import browser_emu


_moduleLogger = logging.getLogger("gvoice.dialer")


class NetworkError(RuntimeError):
	pass


class GVDialer(object):
	"""
	This class encapsulates all of the knowledge necessary to interact with the GoogleVoice servers
	the functions include login, setting up a callback number, and initalting a callback
	"""

	PHONE_TYPE_HOME = 1
	PHONE_TYPE_MOBILE = 2
	PHONE_TYPE_WORK = 3
	PHONE_TYPE_GIZMO = 7

	def __init__(self, cookieFile = None):
		# Important items in this function are the setup of the browser emulation and cookie file
		self._browser = browser_emu.MozillaEmulator(1)
		self._loadedFromCookies = self._browser.load_cookies(cookieFile)

		self._token = ""
		self._accountNum = ""
		self._lastAuthed = 0.0
		self._callbackNumber = ""
		self._callbackNumbers = {}

		# Suprisingly, moving all of these from class to self sped up startup time

		self._validateRe = re.compile("^[0-9]{10,}$")

		self._loginURL = "https://www.google.com/accounts/ServiceLoginAuth"

		SECURE_URL_BASE = "https://www.google.com/voice/"
		SECURE_MOBILE_URL_BASE = SECURE_URL_BASE + "mobile/"
		self._forwardURL = SECURE_MOBILE_URL_BASE + "phones"
		self._tokenURL = SECURE_URL_BASE + "m"
		self._callUrl = SECURE_URL_BASE + "call/connect"
		self._callCancelURL = SECURE_URL_BASE + "call/cancel"
		self._sendSmsURL = SECURE_URL_BASE + "sms/send"

		self._isDndURL = "https://www.google.com/voice/m/donotdisturb"
		self._isDndRe = re.compile(r"""<input.*?id="doNotDisturb".*?checked="(.*?)"\s*/>""")
		self._setDndURL = "https://www.google.com/voice/m/savednd"

		self._downloadVoicemailURL = SECURE_URL_BASE + "media/send_voicemail/"

		self._XML_SEARCH_URL = SECURE_URL_BASE + "inbox/search/"
		self._XML_ACCOUNT_URL = SECURE_URL_BASE + "inbox/contacts/"
		self._XML_RECENT_URL = SECURE_URL_BASE + "inbox/recent/"

		self.XML_FEEDS = (
			'inbox', 'starred', 'all', 'spam', 'trash', 'voicemail', 'sms',
			'recorded', 'placed', 'received', 'missed'
		)
		self._XML_INBOX_URL = SECURE_URL_BASE + "inbox/recent/inbox"
		self._XML_STARRED_URL = SECURE_URL_BASE + "inbox/recent/starred"
		self._XML_ALL_URL = SECURE_URL_BASE + "inbox/recent/all"
		self._XML_SPAM_URL = SECURE_URL_BASE + "inbox/recent/spam"
		self._XML_TRASH_URL = SECURE_URL_BASE + "inbox/recent/trash"
		self._XML_VOICEMAIL_URL = SECURE_URL_BASE + "inbox/recent/voicemail/"
		self._XML_SMS_URL = SECURE_URL_BASE + "inbox/recent/sms/"
		self._XML_RECORDED_URL = SECURE_URL_BASE + "inbox/recent/recorded/"
		self._XML_PLACED_URL = SECURE_URL_BASE + "inbox/recent/placed/"
		self._XML_RECEIVED_URL = SECURE_URL_BASE + "inbox/recent/received/"
		self._XML_MISSED_URL = SECURE_URL_BASE + "inbox/recent/missed/"

		self._contactsURL = SECURE_MOBILE_URL_BASE + "contacts"
		self._contactDetailURL = SECURE_MOBILE_URL_BASE + "contact"

		self._galxRe = re.compile(r"""<input.*?name="GALX".*?value="(.*?)".*?/>""", re.MULTILINE | re.DOTALL)
		self._tokenRe = re.compile(r"""<input.*?name="_rnr_se".*?value="(.*?)"\s*/>""")
		self._accountNumRe = re.compile(r"""<b class="ms\d">(.{14})</b></div>""")
		self._callbackRe = re.compile(r"""\s+(.*?):\s*(.*?)<br\s*/>\s*$""", re.M)

		self._contactsRe = re.compile(r"""<a href="/voice/m/contact/(\d+)">(.*?)</a>""", re.S)
		self._contactsNextRe = re.compile(r""".*<a href="/voice/m/contacts(\?p=\d+)">Next.*?</a>""", re.S)
		self._contactDetailPhoneRe = re.compile(r"""<div.*?>([0-9+\-\(\) \t]+?)<span.*?>\((\w+)\)</span>""", re.S)

		self._seperateVoicemailsRegex = re.compile(r"""^\s*<div id="(\w+)"\s* class=".*?gc-message.*?">""", re.MULTILINE | re.DOTALL)
		self._exactVoicemailTimeRegex = re.compile(r"""<span class="gc-message-time">(.*?)</span>""", re.MULTILINE)
		self._relativeVoicemailTimeRegex = re.compile(r"""<span class="gc-message-relative">(.*?)</span>""", re.MULTILINE)
		self._voicemailNameRegex = re.compile(r"""<a class=.*?gc-message-name-link.*?>(.*?)</a>""", re.MULTILINE | re.DOTALL)
		self._voicemailNumberRegex = re.compile(r"""<input type="hidden" class="gc-text gc-quickcall-ac" value="(.*?)"/>""", re.MULTILINE)
		self._prettyVoicemailNumberRegex = re.compile(r"""<span class="gc-message-type">(.*?)</span>""", re.MULTILINE)
		self._voicemailLocationRegex = re.compile(r"""<span class="gc-message-location">.*?<a.*?>(.*?)</a></span>""", re.MULTILINE)
		self._messagesContactIDRegex = re.compile(r"""<a class=".*?gc-message-name-link.*?">.*?</a>\s*?<span .*?>(.*?)</span>""", re.MULTILINE)
		self._voicemailMessageRegex = re.compile(r"""(<span id="\d+-\d+" class="gc-word-(.*?)">(.*?)</span>|<a .*? class="gc-message-mni">(.*?)</a>)""", re.MULTILINE)
		self._smsFromRegex = re.compile(r"""<span class="gc-message-sms-from">(.*?)</span>""", re.MULTILINE | re.DOTALL)
		self._smsTimeRegex = re.compile(r"""<span class="gc-message-sms-time">(.*?)</span>""", re.MULTILINE | re.DOTALL)
		self._smsTextRegex = re.compile(r"""<span class="gc-message-sms-text">(.*?)</span>""", re.MULTILINE | re.DOTALL)

	def is_quick_login_possible(self):
		"""
		@returns True then is_authed might be enough to login, else full login is required
		"""
		return self._loadedFromCookies or 0.0 < self._lastAuthed

	def is_authed(self, force = False):
		"""
		Attempts to detect a current session
		@note Once logged in try not to reauth more than once a minute.
		@returns If authenticated
		"""
		isRecentledAuthed = (time.time() - self._lastAuthed) < 120
		isPreviouslyAuthed = self._token is not None
		if isRecentledAuthed and isPreviouslyAuthed and not force:
			return True

		try:
			page = self._get_page(self._forwardURL)
			self._grab_account_info(page)
		except Exception, e:
			_moduleLogger.exception(str(e))
			return False

		self._browser.save_cookies()
		self._lastAuthed = time.time()
		return True

	def _get_token(self):
		tokenPage = self._get_page(self._tokenURL)

		galxTokens = self._galxRe.search(tokenPage)
		if galxTokens is not None:
			galxToken = galxTokens.group(1)
		else:
			galxToken = ""
			_moduleLogger.debug("Could not grab GALX token")
		return galxToken

	def _login(self, username, password, token):
		loginData = {
			'Email' : username,
			'Passwd' : password,
			'service': "grandcentral",
			"ltmpl": "mobile",
			"btmpl": "mobile",
			"PersistentCookie": "yes",
			"GALX": token,
			"continue": self._forwardURL,
		}

		loginSuccessOrFailurePage = self._get_page(self._loginURL, loginData)
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

		self._browser.save_cookies()
		self._lastAuthed = time.time()
		return True

	def logout(self):
		self._browser.clear_cookies()
		self._browser.save_cookies()
		self._token = None
		self._lastAuthed = 0.0

	def is_dnd(self):
		isDndPage = self._get_page(self._isDndURL)

		dndGroup = self._isDndRe.search(isDndPage)
		if dndGroup is None:
			return False
		dndStatus = dndGroup.group(1)
		isDnd = True if dndStatus.strip().lower() == "true" else False
		return isDnd

	def set_dnd(self, doNotDisturb):
		dndPostData = {
			"doNotDisturb": 1 if doNotDisturb else 0,
			"_rnr_se": self._token,
		}

		dndPage = self._get_page(self._setDndURL, dndPostData)

	def call(self, outgoingNumber):
		"""
		This is the main function responsible for initating the callback
		"""
		outgoingNumber = self._send_validation(outgoingNumber)
		subscriberNumber = None
		phoneType = guess_phone_type(self._callbackNumber) # @todo Fix this hack

		callData = {
				'outgoingNumber': outgoingNumber,
				'forwardingNumber': self._callbackNumber,
				'subscriberNumber': subscriberNumber or 'undefined',
				'phoneType': str(phoneType),
				'remember': '1',
		}
		_moduleLogger.info("%r" % callData)

		page = self._get_page_with_token(
			self._callUrl,
			callData,
		)
		self._parse_with_validation(page)
		return True

	def cancel(self, outgoingNumber=None):
		"""
		Cancels a call matching outgoing and forwarding numbers (if given). 
		Will raise an error if no matching call is being placed
		"""
		page = self._get_page_with_token(
			self._callCancelURL,
			{
			'outgoingNumber': outgoingNumber or 'undefined',
			'forwardingNumber': self._callbackNumber or 'undefined',
			'cancelType': 'C2C',
			},
		)
		self._parse_with_validation(page)

	def send_sms(self, phoneNumber, message):
		phoneNumber = self._send_validation(phoneNumber)
		page = self._get_page_with_token(
			self._sendSmsURL,
			{
				'phoneNumber': phoneNumber,
				'text': message
			},
		)
		self._parse_with_validation(page)

	def search(self, query):
		"""
		Search your Google Voice Account history for calls, voicemails, and sms
		Returns ``Folder`` instance containting matching messages
		"""
		page = self._get_page(
			self._XML_SEARCH_URL,
			{"q": query},
		)
		json, html = extract_payload(page)
		return json

	def get_feed(self, feed):
		actualFeed = "_XML_%s_URL" % feed.upper()
		feedUrl = getattr(self, actualFeed)

		page = self._get_page(feedUrl)
		json, html = extract_payload(page)

		return json

	def download(self, messageId, adir):
		"""
		Download a voicemail or recorded call MP3 matching the given ``msg``
		which can either be a ``Message`` instance, or a SHA1 identifier. 
		Saves files to ``adir`` (defaults to current directory). 
		Message hashes can be found in ``self.voicemail().messages`` for example. 
		Returns location of saved file.
		"""
		page = self._get_page(self._downloadVoicemailURL, {"id": messageId})
		fn = os.path.join(adir, '%s.mp3' % messageId)
		with open(fn, 'wb') as fo:
			fo.write(page)
		return fn

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
			("Received", self._XML_RECEIVED_URL),
			("Missed", self._XML_MISSED_URL),
			("Placed", self._XML_PLACED_URL),
		):
			flatXml = self._get_page(url)

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
			contactsPage = self._get_page(contactsPageUrl)
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
		detailPage = self._get_page(self._contactDetailURL + '/' + contactId)

		for detail_match in self._contactDetailPhoneRe.finditer(detailPage):
			phoneNumber = detail_match.group(1)
			phoneType = saxutils.unescape(detail_match.group(2))
			yield (phoneType, phoneNumber)

	def get_messages(self):
		voicemailPage = self._get_page(self._XML_VOICEMAIL_URL)
		voicemailHtml = self._grab_html(voicemailPage)
		voicemailJson = self._grab_json(voicemailPage)
		parsedVoicemail = self._parse_voicemail(voicemailHtml)
		voicemails = self._merge_messages(parsedVoicemail, voicemailJson)
		decoratedVoicemails = self._decorate_voicemail(voicemails)

		smsPage = self._get_page(self._XML_SMS_URL)
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
			contactIdGroup = self._messagesContactIDRegex.search(messageHtml)
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
			contactIdGroup = self._messagesContactIDRegex.search(messageHtml)
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

	def _get_page(self, url, data = None, refererUrl = None):
		headers = {}
		if refererUrl is not None:
			headers["Referer"] = refererUrl

		encodedData = urllib.urlencode(data) if data is not None else None

		try:
			page = self._browser.download(url, encodedData, None, headers)
		except urllib2.URLError, e:
			_moduleLogger.error("Translating error: %s" % str(e))
			raise NetworkError("%s is not accesible" % url)

		return page

	def _get_page_with_token(self, url, data = None, refererUrl = None):
		if data is None:
			data = {}
		data['_rnr_se'] = self._token

		page = self._get_page(url, data, refererUrl)

		return page

	def _parse_with_validation(self, page):
		json = parse_json(page)
		validate_response(json)
		return json


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


def safe_eval(s):
	_TRUE_REGEX = re.compile("true")
	_FALSE_REGEX = re.compile("false")
	s = _TRUE_REGEX.sub("True", s)
	s = _FALSE_REGEX.sub("False", s)
	return eval(s, {}, {})


def _fake_parse_json(flattened):
	return safe_eval(flattened)


def _actual_parse_json(flattened):
	return simplejson.loads(flattened)


if simplejson is None:
	parse_json = _fake_parse_json
else:
	parse_json = _actual_parse_json


def extract_payload(flatXml):
	xmlTree = ElementTree.fromstring(flatXml)

	jsonElement = xmlTree.getchildren()[0]
	flatJson = jsonElement.text
	jsonTree = parse_json(flatJson)

	htmlElement = xmlTree.getchildren()[1]
	flatHtml = htmlElement.text

	return jsonTree, flatHtml


def validate_response(response):
	"""
	Validates that the JSON response is A-OK
	"""
	try:
		assert 'ok' in response and response['ok']
	except AssertionError:
		raise RuntimeError('There was a problem with GV: %s' % response)


def guess_phone_type(number):
	if number.startswith("747") or number.startswith("1747"):
		return GVDialer.PHONE_TYPE_GIZMO
	else:
		return GVDialer.PHONE_TYPE_MOBILE


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
	print "Is Dnd: ", backend.is_dnd()
	#print "Setting Dnd", backend.set_dnd(True)
	#print "Is Dnd: ", backend.is_dnd()
	#print "Setting Dnd", backend.set_dnd(False)
	#print "Is Dnd: ", backend.is_dnd()

	#print "Token: ", backend._token
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

	#print "Messages: ",
	#for message in backend.get_messages():
	#	message["messageParts"] = list(message["messageParts"])
	#	pprint.pprint(message)
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
		("isdnd", backend._isDndURL),
		("contacts", backend._contactsURL),

		("account", backend._XML_ACCOUNT_URL),
		("voicemail", backend._XML_VOICEMAIL_URL),
		("sms", backend._XML_SMS_URL),

		("recent", backend._XML_RECENT_URL),
		("placed", backend._XML_PLACED_URL),
		("recieved", backend._XML_RECEIVED_URL),
		("missed", backend._XML_MISSED_URL),
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
	if True:
		grab_debug_info(sys.argv[1], sys.argv[2])
	else:
		test_backend(sys.argv[1], sys.argv[2])
