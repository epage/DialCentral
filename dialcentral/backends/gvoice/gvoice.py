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
import inspect

from xml.sax import saxutils
from xml.etree import ElementTree

try:
	import json as _json
	simplejson = _json
except ImportError:
	try:
		import simplejson as _simplejson
		simplejson = _simplejson
	except ImportError:
		simplejson = None

import browser_emu


_moduleLogger = logging.getLogger(__name__)


class NetworkError(RuntimeError):
	pass


class MessageText(object):

	ACCURACY_LOW = "med1"
	ACCURACY_MEDIUM = "med2"
	ACCURACY_HIGH = "high"

	def __init__(self):
		self.accuracy = None
		self.text = None

	def __str__(self):
		return self.text

	def to_dict(self):
		return to_dict(self)

	def __eq__(self, other):
		return self.accuracy == other.accuracy and self.text == other.text


class Message(object):

	def __init__(self):
		self.whoFrom = None
		self.body = None
		self.when = None

	def __str__(self):
		return "%s (%s): %s" % (
			self.whoFrom,
			self.when,
			"".join(unicode(part) for part in self.body)
		)

	def to_dict(self):
		selfDict = to_dict(self)
		selfDict["body"] = [text.to_dict() for text in self.body] if self.body is not None else None
		return selfDict

	def __eq__(self, other):
		return self.whoFrom == other.whoFrom and self.when == other.when and self.body == other.body


class Conversation(object):

	TYPE_VOICEMAIL = "Voicemail"
	TYPE_SMS = "SMS"

	def __init__(self):
		self.type = None
		self.id = None
		self.contactId = None
		self.name = None
		self.location = None
		self.prettyNumber = None
		self.number = None

		self.time = None
		self.relTime = None
		self.messages = None
		self.isRead = None
		self.isSpam = None
		self.isTrash = None
		self.isArchived = None

	def __cmp__(self, other):
		cmpValue = cmp(self.contactId, other.contactId)
		if cmpValue != 0:
			return cmpValue

		cmpValue = cmp(self.time, other.time)
		if cmpValue != 0:
			return cmpValue

		cmpValue = cmp(self.id, other.id)
		if cmpValue != 0:
			return cmpValue

	def to_dict(self):
		selfDict = to_dict(self)
		selfDict["messages"] = [message.to_dict() for message in self.messages] if self.messages is not None else None
		return selfDict


class GVoiceBackend(object):
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

		self._validateRe = re.compile("^\+?[0-9]{10,}$")

		self._loginURL = "https://www.google.com/accounts/ServiceLoginAuth"

		SECURE_URL_BASE = "https://www.google.com/voice/"
		SECURE_MOBILE_URL_BASE = SECURE_URL_BASE + "mobile/"
		self._tokenURL = SECURE_URL_BASE + "m"
		self._callUrl = SECURE_URL_BASE + "call/connect"
		self._callCancelURL = SECURE_URL_BASE + "call/cancel"
		self._sendSmsURL = SECURE_URL_BASE + "sms/send"

		self._isDndURL = "https://www.google.com/voice/m/donotdisturb"
		self._isDndRe = re.compile(r"""<input.*?id="doNotDisturb".*?checked="(.*?)"\s*/>""")
		self._setDndURL = "https://www.google.com/voice/m/savednd"

		self._downloadVoicemailURL = SECURE_URL_BASE + "media/send_voicemail/"
		self._markAsReadURL = SECURE_URL_BASE + "m/mark"
		self._archiveMessageURL = SECURE_URL_BASE + "m/archive"

		self._XML_SEARCH_URL = SECURE_URL_BASE + "inbox/search/"
		self._XML_ACCOUNT_URL = SECURE_URL_BASE + "contacts/"
		# HACK really this redirects to the main pge and we are grabbing some javascript
		self._XML_CONTACTS_URL = "http://www.google.com/voice/inbox/search/contact"
		self._CSV_CONTACTS_URL = "http://mail.google.com/mail/contacts/data/export"
		self._JSON_CONTACTS_URL = SECURE_URL_BASE + "b/0/request/user"
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
		self._JSON_SMS_URL = SECURE_URL_BASE + "b/0/request/messages/"
		self._JSON_SMS_COUNT_URL = SECURE_URL_BASE + "b/0/request/unread"
		self._XML_RECORDED_URL = SECURE_URL_BASE + "inbox/recent/recorded/"
		self._XML_PLACED_URL = SECURE_URL_BASE + "inbox/recent/placed/"
		self._XML_RECEIVED_URL = SECURE_URL_BASE + "inbox/recent/received/"
		self._XML_MISSED_URL = SECURE_URL_BASE + "inbox/recent/missed/"

		self._galxRe = re.compile(r"""<input.*?name="GALX".*?value="(.*?)".*?/>""", re.MULTILINE | re.DOTALL)

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
		@returns True then refresh_account_info might be enough to login, else full login is required
		"""
		return self._loadedFromCookies or 0.0 < self._lastAuthed

	def refresh_account_info(self):
		try:
			page = self._get_page(self._JSON_CONTACTS_URL)
			accountData = self._grab_account_info(page)
		except Exception, e:
			_moduleLogger.exception(str(e))
			return None

		self._browser.save_cookies()
		self._lastAuthed = time.time()
		return accountData

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
			"continue": self._JSON_CONTACTS_URL,
		}

		loginSuccessOrFailurePage = self._get_page(self._loginURL, loginData)
		return loginSuccessOrFailurePage

	def login(self, username, password):
		"""
		Attempt to login to GoogleVoice
		@returns Whether login was successful or not
		@blocks
		"""
		self.logout()
		galxToken = self._get_token()
		loginSuccessOrFailurePage = self._login(username, password, galxToken)

		try:
			accountData = self._grab_account_info(loginSuccessOrFailurePage)
		except Exception, e:
			# Retry in case the redirect failed
			# luckily refresh_account_info does everything we need for a retry
			accountData = self.refresh_account_info()
			if accountData is None:
				_moduleLogger.exception(str(e))
				return None
			_moduleLogger.info("Redirection failed on initial login attempt, auto-corrected for this")

		self._browser.save_cookies()
		self._lastAuthed = time.time()
		return accountData

	def persist(self):
		self._browser.save_cookies()

	def shutdown(self):
		self._browser.save_cookies()
		self._token = None
		self._lastAuthed = 0.0

	def logout(self):
		self._browser.clear_cookies()
		self._browser.save_cookies()
		self._token = None
		self._lastAuthed = 0.0
		self._callbackNumbers = {}

	def is_dnd(self):
		"""
		@blocks
		"""
		isDndPage = self._get_page(self._isDndURL)

		dndGroup = self._isDndRe.search(isDndPage)
		if dndGroup is None:
			return False
		dndStatus = dndGroup.group(1)
		isDnd = True if dndStatus.strip().lower() == "true" else False
		return isDnd

	def set_dnd(self, doNotDisturb):
		"""
		@blocks
		"""
		dndPostData = {
			"doNotDisturb": 1 if doNotDisturb else 0,
		}

		dndPage = self._get_page_with_token(self._setDndURL, dndPostData)

	def call(self, outgoingNumber):
		"""
		This is the main function responsible for initating the callback
		@blocks
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
		@blocks
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

	def send_sms(self, phoneNumbers, message):
		"""
		@blocks
		"""
		validatedPhoneNumbers = [
			self._send_validation(phoneNumber)
			for phoneNumber in phoneNumbers
		]
		flattenedPhoneNumbers = ",".join(validatedPhoneNumbers)
		page = self._get_page_with_token(
			self._sendSmsURL,
			{
				'phoneNumber': flattenedPhoneNumbers,
				'text': unicode(message).encode("utf-8"),
			},
		)
		self._parse_with_validation(page)

	def search(self, query):
		"""
		Search your Google Voice Account history for calls, voicemails, and sms
		Returns ``Folder`` instance containting matching messages
		@blocks
		"""
		page = self._get_page(
			self._XML_SEARCH_URL,
			{"q": query},
		)
		json, html = extract_payload(page)
		return json

	def get_feed(self, feed):
		"""
		@blocks
		"""
		actualFeed = "_XML_%s_URL" % feed.upper()
		feedUrl = getattr(self, actualFeed)

		page = self._get_page(feedUrl)
		json, html = extract_payload(page)

		return json

	def recording_url(self, messageId):
		url = self._downloadVoicemailURL+messageId
		return url

	def download(self, messageId, targetPath):
		"""
		Download a voicemail or recorded call MP3 matching the given ``msg``
		which can either be a ``Message`` instance, or a SHA1 identifier. 
		Message hashes can be found in ``self.voicemail().messages`` for example. 
		@returns location of saved file.
		@blocks
		"""
		page = self._get_page(self.recording_url(messageId))
		with open(targetPath, 'wb') as fo:
			fo.write(page)

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
		return self._callbackNumbers

	def set_callback_number(self, callbacknumber):
		"""
		Set the number that GoogleVoice calls
		@param callbacknumber should be a proper 10 digit number
		"""
		self._callbackNumber = callbacknumber
		_moduleLogger.info("Callback number changed: %r" % self._callbackNumber)
		return True

	def get_callback_number(self):
		"""
		@returns Current callback number or None
		"""
		return self._callbackNumber

	def get_received_calls(self):
		"""
		@returns Iterable of (personsName, phoneNumber, exact date, relative date, action)
		@blocks
		"""
		return self._parse_recent(self._get_page(self._XML_RECEIVED_URL))

	def get_missed_calls(self):
		"""
		@returns Iterable of (personsName, phoneNumber, exact date, relative date, action)
		@blocks
		"""
		return self._parse_recent(self._get_page(self._XML_MISSED_URL))

	def get_placed_calls(self):
		"""
		@returns Iterable of (personsName, phoneNumber, exact date, relative date, action)
		@blocks
		"""
		return self._parse_recent(self._get_page(self._XML_PLACED_URL))

	def get_csv_contacts(self):
		data = {
			"groupToExport": "mine",
			"exportType": "ALL",
			"out": "OUTLOOK_CSV",
		}
		encodedData = urllib.urlencode(data)
		contacts = self._get_page(self._CSV_CONTACTS_URL+"?"+encodedData)
		return contacts

	def get_voicemails(self):
		"""
		@blocks
		"""
		voicemailPage = self._get_page(self._XML_VOICEMAIL_URL)
		voicemailHtml = self._grab_html(voicemailPage)
		voicemailJson = self._grab_json(voicemailPage)
		if voicemailJson is None:
			return ()
		parsedVoicemail = self._parse_voicemail(voicemailHtml)
		voicemails = self._merge_conversation_sources(parsedVoicemail, voicemailJson)
		return voicemails

	def get_texts(self):
		"""
		@blocks
		"""
		smsPage = self._get_page(self._XML_SMS_URL)
		smsHtml = self._grab_html(smsPage)
		smsJson = self._grab_json(smsPage)
		if smsJson is None:
			return ()
		parsedSms = self._parse_sms(smsHtml)
		smss = self._merge_conversation_sources(parsedSms, smsJson)
		return smss

	def get_unread_counts(self):
		countPage = self._get_page(self._JSON_SMS_COUNT_URL)
		counts = parse_json(countPage)
		counts = counts["unreadCounts"]
		return counts

	def mark_message(self, messageId, asRead):
		"""
		@blocks
		"""
		postData = {
			"read": 1 if asRead else 0,
			"id": messageId,
		}

		markPage = self._get_page(self._markAsReadURL, postData)

	def archive_message(self, messageId):
		"""
		@blocks
		"""
		postData = {
			"id": messageId,
		}

		markPage = self._get_page(self._archiveMessageURL, postData)

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
		accountData = parse_json(page)
		self._token = accountData["r"]
		self._accountNum = accountData["number"]["raw"]
		for callback in accountData["phones"].itervalues():
			self._callbackNumbers[callback["phoneNumber"]] = callback["name"]
		if len(self._callbackNumbers) == 0:
			_moduleLogger.debug("Could not extract callback numbers from GoogleVoice (the troublesome page follows):\n%s" % page)
		return accountData

	def _send_validation(self, number):
		if not self.is_valid_syntax(number):
			raise ValueError('Number is not valid: "%s"' % number)
		return number

	def _parse_recent(self, recentPage):
		allRecentHtml = self._grab_html(recentPage)
		allRecentData = self._parse_history(allRecentHtml)
		for recentCallData in allRecentData:
			yield recentCallData

	def _parse_history(self, historyHtml):
		splitVoicemail = self._seperateVoicemailsRegex.split(historyHtml)
		for messageId, messageHtml in itergroup(splitVoicemail[1:], 2):
			exactTimeGroup = self._exactVoicemailTimeRegex.search(messageHtml)
			exactTime = exactTimeGroup.group(1).strip() if exactTimeGroup else ""
			exactTime = google_strptime(exactTime)
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

			yield {
				"id": messageId.strip(),
				"contactId": contactId,
				"name": unescape(name),
				"time": exactTime,
				"relTime": relativeTime,
				"prettyNumber": prettyNumber,
				"number": number,
				"location": unescape(location),
			}

	@staticmethod
	def _interpret_voicemail_regex(group):
		quality, content, number = group.group(2), group.group(3), group.group(4)
		text = MessageText()
		if quality is not None and content is not None:
			text.accuracy = quality
			text.text = unescape(content)
			return text
		elif number is not None:
			text.accuracy = MessageText.ACCURACY_HIGH
			text.text = number
			return text

	def _parse_voicemail(self, voicemailHtml):
		splitVoicemail = self._seperateVoicemailsRegex.split(voicemailHtml)
		for messageId, messageHtml in itergroup(splitVoicemail[1:], 2):
			conv = Conversation()
			conv.type = Conversation.TYPE_VOICEMAIL
			conv.id = messageId.strip()

			exactTimeGroup = self._exactVoicemailTimeRegex.search(messageHtml)
			exactTimeText = exactTimeGroup.group(1).strip() if exactTimeGroup else ""
			conv.time = google_strptime(exactTimeText)
			relativeTimeGroup = self._relativeVoicemailTimeRegex.search(messageHtml)
			conv.relTime = relativeTimeGroup.group(1).strip() if relativeTimeGroup else ""
			locationGroup = self._voicemailLocationRegex.search(messageHtml)
			conv.location = unescape(locationGroup.group(1).strip() if locationGroup else "")

			nameGroup = self._voicemailNameRegex.search(messageHtml)
			conv.name = unescape(nameGroup.group(1).strip() if nameGroup else "")
			numberGroup = self._voicemailNumberRegex.search(messageHtml)
			conv.number = numberGroup.group(1).strip() if numberGroup else ""
			prettyNumberGroup = self._prettyVoicemailNumberRegex.search(messageHtml)
			conv.prettyNumber = prettyNumberGroup.group(1).strip() if prettyNumberGroup else ""
			contactIdGroup = self._messagesContactIDRegex.search(messageHtml)
			conv.contactId = contactIdGroup.group(1).strip() if contactIdGroup else ""

			messageGroups = self._voicemailMessageRegex.finditer(messageHtml)
			messageParts = [
				self._interpret_voicemail_regex(group)
				for group in messageGroups
			] if messageGroups else ((MessageText.ACCURACY_LOW, "No Transcription"), )
			message = Message()
			message.body = messageParts
			message.whoFrom = conv.name
			try:
				message.when = conv.time.strftime("%I:%M %p")
			except ValueError:
				_moduleLogger.exception("Confusing time provided: %r" % conv.time)
				message.when = "Unknown"
			conv.messages = (message, )

			yield conv

	@staticmethod
	def _interpret_sms_message_parts(fromPart, textPart, timePart):
		text = MessageText()
		text.accuracy = MessageText.ACCURACY_MEDIUM
		text.text = unescape(textPart)

		message = Message()
		message.body = (text, )
		message.whoFrom = fromPart
		message.when = timePart

		return message

	def _parse_sms(self, smsHtml):
		splitSms = self._seperateVoicemailsRegex.split(smsHtml)
		for messageId, messageHtml in itergroup(splitSms[1:], 2):
			conv = Conversation()
			conv.type = Conversation.TYPE_SMS
			conv.id = messageId.strip()

			exactTimeGroup = self._exactVoicemailTimeRegex.search(messageHtml)
			exactTimeText = exactTimeGroup.group(1).strip() if exactTimeGroup else ""
			conv.time = google_strptime(exactTimeText)
			relativeTimeGroup = self._relativeVoicemailTimeRegex.search(messageHtml)
			conv.relTime = relativeTimeGroup.group(1).strip() if relativeTimeGroup else ""
			conv.location = ""

			nameGroup = self._voicemailNameRegex.search(messageHtml)
			conv.name = unescape(nameGroup.group(1).strip() if nameGroup else "")
			numberGroup = self._voicemailNumberRegex.search(messageHtml)
			conv.number = numberGroup.group(1).strip() if numberGroup else ""
			prettyNumberGroup = self._prettyVoicemailNumberRegex.search(messageHtml)
			conv.prettyNumber = prettyNumberGroup.group(1).strip() if prettyNumberGroup else ""
			contactIdGroup = self._messagesContactIDRegex.search(messageHtml)
			conv.contactId = contactIdGroup.group(1).strip() if contactIdGroup else ""

			fromGroups = self._smsFromRegex.finditer(messageHtml)
			fromParts = (group.group(1).strip() for group in fromGroups)
			textGroups = self._smsTextRegex.finditer(messageHtml)
			textParts = (group.group(1).strip() for group in textGroups)
			timeGroups = self._smsTimeRegex.finditer(messageHtml)
			timeParts = (group.group(1).strip() for group in timeGroups)

			messageParts = itertools.izip(fromParts, textParts, timeParts)
			messages = [self._interpret_sms_message_parts(*parts) for parts in messageParts]
			conv.messages = messages

			yield conv

	@staticmethod
	def _merge_conversation_sources(parsedMessages, json):
		for message in parsedMessages:
			jsonItem = json["messages"][message.id]
			message.isRead = jsonItem["isRead"]
			message.isSpam = jsonItem["isSpam"]
			message.isTrash = jsonItem["isTrash"]
			message.isArchived = "inbox" not in jsonItem["labels"]
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
		self._validate_response(json)
		return json

	def _validate_response(self, response):
		"""
		Validates that the JSON response is A-OK
		"""
		try:
			assert response is not None, "Response not provided"
			assert 'ok' in response, "Response lacks status"
			assert response['ok'], "Response not good"
		except AssertionError:
			try:
				if response["data"]["code"] == 20:
					raise RuntimeError(
"""Ambiguous error 20 returned by Google Voice.
Please verify you have configured your callback number (currently "%s").  If it is configured some other suspected causes are: non-verified callback numbers, and Gizmo5 callback numbers.""" % self._callbackNumber)
			except KeyError:
				pass
			raise RuntimeError('There was a problem with GV: %s' % response)


_UNESCAPE_ENTITIES = {
 "&quot;": '"',
 "&nbsp;": " ",
 "&#39;": "'",
}


def unescape(text):
	plain = saxutils.unescape(text, _UNESCAPE_ENTITIES)
	return plain


def google_strptime(time):
	"""
	Hack: Google always returns the time in the same locale.  Sadly if the
	local system's locale is different, there isn't a way to perfectly handle
	the time.  So instead we handle implement some time formatting
	"""
	try:
		abbrevTime = time[:-3]
		parsedTime = datetime.datetime.strptime(abbrevTime, "%m/%d/%y %I:%M")
	except:
		_moduleLogger.exception("Fooey, going with a dummy date")
		parsedTime = datetime.datetime(1, 1, 1)
		return parsedTime
	if time.endswith("PM"):
		parsedTime += datetime.timedelta(hours=12)
	elif time.endswith("AM"):
		pass
	else:
		_moduleLogger.error("Unknown time of date for %r" % time)
	return parsedTime


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
	_COMMENT_REGEX = re.compile("^\s+//.*$", re.M)
	s = _TRUE_REGEX.sub("True", s)
	s = _FALSE_REGEX.sub("False", s)
	s = _COMMENT_REGEX.sub("#", s)
	try:
		results = eval(s, {}, {})
	except SyntaxError:
		_moduleLogger.exception("Oops")
		results = None
	return results


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


def guess_phone_type(number):
	if number.startswith("747") or number.startswith("1747") or number.startswith("+1747"):
		return GVoiceBackend.PHONE_TYPE_GIZMO
	else:
		return GVoiceBackend.PHONE_TYPE_MOBILE


def get_sane_callback(backend):
	"""
	Try to set a sane default callback number on these preferences
	1) 1747 numbers ( Gizmo )
	2) anything with gizmo in the name
	3) anything with computer in the name
	4) the first value
	"""
	numbers = backend.get_callback_numbers()

	priorityOrderedCriteria = [
		("\+1747", None),
		("1747", None),
		("747", None),
		(None, "gizmo"),
		(None, "computer"),
		(None, "sip"),
		(None, None),
	]

	for numberCriteria, descriptionCriteria in priorityOrderedCriteria:
		numberMatcher = None
		descriptionMatcher = None
		if numberCriteria is not None:
			numberMatcher = re.compile(numberCriteria)
		elif descriptionCriteria is not None:
			descriptionMatcher = re.compile(descriptionCriteria, re.I)

		for number, description in numbers.iteritems():
			if numberMatcher is not None and numberMatcher.match(number) is None:
				continue
			if descriptionMatcher is not None and descriptionMatcher.match(description) is None:
				continue
			return number


def set_sane_callback(backend):
	"""
	Try to set a sane default callback number on these preferences
	1) 1747 numbers ( Gizmo )
	2) anything with gizmo in the name
	3) anything with computer in the name
	4) the first value
	"""
	number = get_sane_callback(backend)
	backend.set_callback_number(number)


def _is_not_special(name):
	return not name.startswith("_") and name[0].lower() == name[0] and "_" not in name


def to_dict(obj):
	members = inspect.getmembers(obj)
	return dict((name, value) for (name, value) in members if _is_not_special(name))


def grab_debug_info(username, password):
	cookieFile = os.path.join(".", "raw_cookies.txt")
	try:
		os.remove(cookieFile)
	except OSError:
		pass

	backend = GVoiceBackend(cookieFile)
	browser = backend._browser

	_TEST_WEBPAGES = [
		("token", backend._tokenURL),
		("login", backend._loginURL),
		("isdnd", backend._isDndURL),
		("account", backend._XML_ACCOUNT_URL),
		("html_contacts", backend._XML_CONTACTS_URL),
		("contacts", backend._JSON_CONTACTS_URL),
		("csv", backend._CSV_CONTACTS_URL),

		("voicemail", backend._XML_VOICEMAIL_URL),
		("html_sms", backend._XML_SMS_URL),
		("sms", backend._JSON_SMS_URL),
		("count", backend._JSON_SMS_COUNT_URL),

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
		# luckily refresh_account_info does everything we need for a retry
		loggedIn = backend.refresh_account_info() is not None
		if not loggedIn:
			raise

	# Get Pages
	print "Grabbing post-login pages"
	for name, url in _TEST_WEBPAGES:
		try:
			page = browser.download(url)
		except StandardError, e:
			print str(e)
			continue
		print "\tWriting to file"
		with open("loggedin_%s.txt" % name, "w") as f:
			f.write(page)

	# Cookies
	browser.save_cookies()
	print "\tWriting cookies to file"
	with open("cookies.txt", "w") as f:
		f.writelines(
			"%s: %s\n" % (c.name, c.value)
			for c in browser._cookies
		)


def grab_voicemails(username, password):
	cookieFile = os.path.join(".", "raw_cookies.txt")
	try:
		os.remove(cookieFile)
	except OSError:
		pass

	backend = GVoiceBackend(cookieFile)
	backend.login(username, password)
	voicemails = list(backend.get_voicemails())
	for voicemail in voicemails:
		print voicemail.id
		backend.download(voicemail.id, ".")


def main():
	import sys
	logging.basicConfig(level=logging.DEBUG)
	args = sys.argv
	if 3 <= len(args):
		username = args[1]
		password = args[2]

	grab_debug_info(username, password)
	grab_voicemails(username, password)


if __name__ == "__main__":
	main()
