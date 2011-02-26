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

import itertools
import logging

from gvoice import gvoice

from util import io as io_utils


_moduleLogger = logging.getLogger(__name__)


class GVDialer(object):

	def __init__(self, cookieFile = None):
		self._gvoice = gvoice.GVoiceBackend(cookieFile)

	def is_quick_login_possible(self):
		"""
		@returns True then refresh_account_info might be enough to login, else full login is required
		"""
		return self._gvoice.is_quick_login_possible()

	def refresh_account_info(self):
		return self._gvoice.refresh_account_info()

	def login(self, username, password):
		"""
		Attempt to login to GoogleVoice
		@returns Whether login was successful or not
		"""
		return self._gvoice.login(username, password)

	def logout(self):
		return self._gvoice.logout()

	def persist(self):
		return self._gvoice.persist()

	def is_dnd(self):
		return self._gvoice.is_dnd()

	def set_dnd(self, doNotDisturb):
		return self._gvoice.set_dnd(doNotDisturb)

	def call(self, outgoingNumber):
		"""
		This is the main function responsible for initating the callback
		"""
		return self._gvoice.call(outgoingNumber)

	def cancel(self, outgoingNumber=None):
		"""
		Cancels a call matching outgoing and forwarding numbers (if given). 
		Will raise an error if no matching call is being placed
		"""
		return self._gvoice.cancel(outgoingNumber)

	def send_sms(self, phoneNumbers, message):
		self._gvoice.send_sms(phoneNumbers, message)

	def search(self, query):
		"""
		Search your Google Voice Account history for calls, voicemails, and sms
		Returns ``Folder`` instance containting matching messages
		"""
		return self._gvoice.search(query)

	def get_feed(self, feed):
		return self._gvoice.get_feed(feed)

	def download(self, messageId, adir):
		"""
		Download a voicemail or recorded call MP3 matching the given ``msg``
		which can either be a ``Message`` instance, or a SHA1 identifier. 
		Saves files to ``adir`` (defaults to current directory). 
		Message hashes can be found in ``self.voicemail().messages`` for example. 
		Returns location of saved file.
		"""
		return self._gvoice.download(messageId, adir)

	def is_valid_syntax(self, number):
		"""
		@returns If This number be called ( syntax validation only )
		"""
		return self._gvoice.is_valid_syntax(number)

	def get_account_number(self):
		"""
		@returns The GoogleVoice phone number
		"""
		return self._gvoice.get_account_number()

	def get_callback_numbers(self):
		"""
		@returns a dictionary mapping call back numbers to descriptions
		@note These results are cached for 30 minutes.
		"""
		return self._gvoice.get_callback_numbers()

	def set_callback_number(self, callbacknumber):
		"""
		Set the number that GoogleVoice calls
		@param callbacknumber should be a proper 10 digit number
		"""
		return self._gvoice.set_callback_number(callbacknumber)

	def get_callback_number(self):
		"""
		@returns Current callback number or None
		"""
		return self._gvoice.get_callback_number()

	def get_recent(self):
		"""
		@returns Iterable of (personsName, phoneNumber, exact date, relative date, action)
		"""
		return list(self._gvoice.get_recent())

	def get_messages(self):
		messages = list(self._get_messages())
		messages.sort(key=lambda message: message["time"])
		return messages

	def _get_messages(self):
		voicemails = self._gvoice.get_voicemails()
		smss = self._gvoice.get_texts()
		conversations = itertools.chain(voicemails, smss)
		for conversation in conversations:
			messages = conversation.messages
			messageParts = [
				(message.whoFrom, self._format_message(message), message.when)
				for message in messages
			]

			messageDetails = {
				"id": conversation.id,
				"contactId": conversation.contactId,
				"name": conversation.name,
				"time": conversation.time,
				"relTime": conversation.relTime,
				"prettyNumber": conversation.prettyNumber,
				"number": conversation.number,
				"location": conversation.location,
				"messageParts": messageParts,
				"type": conversation.type,
				"isRead": conversation.isRead,
				"isTrash": conversation.isTrash,
				"isSpam": conversation.isSpam,
				"isArchived": conversation.isArchived,
			}
			yield messageDetails

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

	def _format_message(self, message):
		messagePartFormat = {
			"med1": "<i>%s</i>",
			"med2": "%s",
			"high": "<b>%s</b>",
		}
		return " ".join(
			messagePartFormat[text.accuracy] % io_utils.escape(text.text)
			for text in message.body
		)


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
