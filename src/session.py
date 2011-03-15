from __future__ import with_statement

import os
import time
import datetime
import contextlib
import logging

try:
	import cPickle
	pickle = cPickle
except ImportError:
	import pickle

from PyQt4 import QtCore

from util import qore_utils
from util import qui_utils
from util import concurrent
from util import misc as misc_utils

import constants


_moduleLogger = logging.getLogger(__name__)


class _DraftContact(object):

	def __init__(self, messageId, title, description, numbersWithDescriptions):
		self.messageId = messageId
		self.title = title
		self.description = description
		self.numbers = numbersWithDescriptions
		self.selectedNumber = numbersWithDescriptions[0][0]


class Draft(QtCore.QObject):

	sendingMessage = QtCore.pyqtSignal()
	sentMessage = QtCore.pyqtSignal()
	calling = QtCore.pyqtSignal()
	called = QtCore.pyqtSignal()
	cancelling = QtCore.pyqtSignal()
	cancelled = QtCore.pyqtSignal()
	error = QtCore.pyqtSignal(str)

	recipientsChanged = QtCore.pyqtSignal()

	def __init__(self, pool, backend, errorLog):
		QtCore.QObject.__init__(self)
		self._errorLog = errorLog
		self._contacts = {}
		self._pool = pool
		self._backend = backend
		self._busyReason = None
		self._message = ""

	def send(self):
		assert 0 < len(self._contacts), "No contacts selected"
		assert 0 < len(self._message), "No message to send"
		numbers = [misc_utils.make_ugly(contact.selectedNumber) for contact in self._contacts.itervalues()]
		le = concurrent.AsyncLinearExecution(self._pool, self._send)
		le.start(numbers, self._message)

	def call(self):
		assert len(self._contacts) == 1, "Must select 1 and only 1 contact"
		assert len(self._message) == 0, "Cannot send message with call"
		(contact, ) = self._contacts.itervalues()
		number = misc_utils.make_ugly(contact.selectedNumber)
		le = concurrent.AsyncLinearExecution(self._pool, self._call)
		le.start(number)

	def cancel(self):
		le = concurrent.AsyncLinearExecution(self._pool, self._cancel)
		le.start()

	def _get_message(self):
		return self._message

	def _set_message(self, message):
		self._message = message

	message = property(_get_message, _set_message)

	def add_contact(self, contactId, messageId, title, description, numbersWithDescriptions):
		if self._busyReason is not None:
			raise RuntimeError("Please wait for %r" % self._busyReason)
		# Allow overwriting of contacts so that the message can be updated and the SMS dialog popped back up
		contactDetails = _DraftContact(messageId, title, description, numbersWithDescriptions)
		self._contacts[contactId] = contactDetails
		self.recipientsChanged.emit()

	def remove_contact(self, contactId):
		if self._busyReason is not None:
			raise RuntimeError("Please wait for %r" % self._busyReason)
		assert contactId in self._contacts, "Contact missing"
		del self._contacts[contactId]
		self.recipientsChanged.emit()

	def get_contacts(self):
		return self._contacts.iterkeys()

	def get_num_contacts(self):
		return len(self._contacts)

	def get_message_id(self, cid):
		return self._contacts[cid].messageId

	def get_title(self, cid):
		return self._contacts[cid].title

	def get_description(self, cid):
		return self._contacts[cid].description

	def get_numbers(self, cid):
		return self._contacts[cid].numbers

	def get_selected_number(self, cid):
		return self._contacts[cid].selectedNumber

	def set_selected_number(self, cid, number):
		# @note I'm lazy, this isn't firing any kind of signal since only one
		# controller right now and that is the viewer
		assert number in (nWD[0] for nWD in self._contacts[cid].numbers), "Number not selectable"
		self._contacts[cid].selectedNumber = number

	def clear(self):
		if self._busyReason is not None:
			raise RuntimeError("Please wait for %r" % self._busyReason)
		self._clear()

	def _clear(self):
		oldContacts = self._contacts
		self._contacts = {}
		self._message = ""
		if oldContacts:
			self.recipientsChanged.emit()

	@contextlib.contextmanager
	def _busy(self, message):
		if self._busyReason is not None:
			raise RuntimeError("Already busy doing %r" % self._busyReason)
		try:
			self._busyReason = message
			yield
		finally:
			self._busyReason = None

	def _send(self, numbers, text):
		self.sendingMessage.emit()
		try:
			with self._busy("Sending Text"):
				with qui_utils.notify_busy(self._errorLog, "Sending Text"):
					yield (
						self._backend[0].send_sms,
						(numbers, text),
						{},
					)
				self.sentMessage.emit()
				self._clear()
		except Exception, e:
			_moduleLogger.exception("Reporting error to user")
			self.error.emit(str(e))

	def _call(self, number):
		self.calling.emit()
		try:
			with self._busy("Calling"):
				with qui_utils.notify_busy(self._errorLog, "Calling"):
					yield (
						self._backend[0].call,
						(number, ),
						{},
					)
				self.called.emit()
				self._clear()
		except Exception, e:
			_moduleLogger.exception("Reporting error to user")
			self.error.emit(str(e))

	def _cancel(self):
		self.cancelling.emit()
		try:
			with qui_utils.notify_busy(self._errorLog, "Cancelling"):
				yield (
					self._backend[0].cancel,
					(),
					{},
				)
			self.cancelled.emit()
		except Exception, e:
			_moduleLogger.exception("Reporting error to user")
			self.error.emit(str(e))


class Session(QtCore.QObject):

	# @todo Somehow add support for csv contacts

	stateChange = QtCore.pyqtSignal(str)
	loggedOut = QtCore.pyqtSignal()
	loggedIn = QtCore.pyqtSignal()
	callbackNumberChanged = QtCore.pyqtSignal(str)

	accountUpdated = QtCore.pyqtSignal()
	messagesUpdated = QtCore.pyqtSignal()
	newMessages = QtCore.pyqtSignal()
	historyUpdated = QtCore.pyqtSignal()
	dndStateChange = QtCore.pyqtSignal(bool)
	voicemailAvailable = QtCore.pyqtSignal(str, str)

	error = QtCore.pyqtSignal(str)

	LOGGEDOUT_STATE = "logged out"
	LOGGINGIN_STATE = "logging in"
	LOGGEDIN_STATE = "logged in"

	MESSAGE_TEXTS = "Text"
	MESSAGE_VOICEMAILS = "Voicemail"
	MESSAGE_ALL = "All"

	_OLDEST_COMPATIBLE_FORMAT_VERSION = misc_utils.parse_version("1.3.0")

	_LOGGEDOUT_TIME = -1
	_LOGGINGIN_TIME = 0

	def __init__(self, errorLog, cachePath = None):
		QtCore.QObject.__init__(self)
		self._errorLog = errorLog
		self._pool = qore_utils.AsyncPool()
		self._backend = []
		self._loggedInTime = self._LOGGEDOUT_TIME
		self._loginOps = []
		self._cachePath = cachePath
		self._voicemailCachePath = None
		self._username = None
		self._draft = Draft(self._pool, self._backend, self._errorLog)

		self._contacts = {}
		self._accountUpdateTime = datetime.datetime(1971, 1, 1)
		self._messages = []
		self._cleanMessages = []
		self._messageUpdateTime = datetime.datetime(1971, 1, 1)
		self._history = []
		self._historyUpdateTime = datetime.datetime(1971, 1, 1)
		self._dnd = False
		self._callback = ""

	@property
	def state(self):
		return {
			self._LOGGEDOUT_TIME: self.LOGGEDOUT_STATE,
			self._LOGGINGIN_TIME: self.LOGGINGIN_STATE,
		}.get(self._loggedInTime, self.LOGGEDIN_STATE)

	@property
	def draft(self):
		return self._draft

	def login(self, username, password):
		assert self.state == self.LOGGEDOUT_STATE, "Can only log-in when logged out (currently %s" % self.state
		assert username != "", "No username specified"
		if self._cachePath is not None:
			cookiePath = os.path.join(self._cachePath, "%s.cookies" % username)
		else:
			cookiePath = None

		if self._username != username or not self._backend:
			from backends import gv_backend
			del self._backend[:]
			self._backend[0:0] = [gv_backend.GVDialer(cookiePath)]

		self._pool.start()
		le = concurrent.AsyncLinearExecution(self._pool, self._login)
		le.start(username, password)

	def logout(self):
		assert self.state != self.LOGGEDOUT_STATE, "Can only logout if logged in (currently %s" % self.state
		_moduleLogger.info("Logging out")
		self._pool.stop()
		self._loggedInTime = self._LOGGEDOUT_TIME
		self._backend[0].persist()
		self._save_to_cache()
		self._clear_voicemail_cache()
		self.stateChange.emit(self.LOGGEDOUT_STATE)
		self.loggedOut.emit()

	def clear(self):
		assert self.state == self.LOGGEDOUT_STATE, "Can only clear when logged out (currently %s" % self.state
		self._backend[0].logout()
		del self._backend[0]
		self._clear_cache()
		self._draft.clear()

	def logout_and_clear(self):
		assert self.state != self.LOGGEDOUT_STATE, "Can only logout if logged in (currently %s" % self.state
		_moduleLogger.info("Logging out and clearing the account")
		self._pool.stop()
		self._loggedInTime = self._LOGGEDOUT_TIME
		self.clear()
		self.stateChange.emit(self.LOGGEDOUT_STATE)
		self.loggedOut.emit()

	def update_account(self, force = True):
		if not force and self._contacts:
			return
		le = concurrent.AsyncLinearExecution(self._pool, self._update_account), (), {}
		self._perform_op_while_loggedin(le)

	def get_contacts(self):
		return self._contacts

	def get_when_contacts_updated(self):
		return self._accountUpdateTime

	def update_messages(self, messageType, force = True):
		if not force and self._messages:
			return
		le = concurrent.AsyncLinearExecution(self._pool, self._update_messages), (messageType, ), {}
		self._perform_op_while_loggedin(le)

	def get_messages(self):
		return self._messages

	def get_when_messages_updated(self):
		return self._messageUpdateTime

	def update_history(self, force = True):
		if not force and self._history:
			return
		le = concurrent.AsyncLinearExecution(self._pool, self._update_history), (), {}
		self._perform_op_while_loggedin(le)

	def get_history(self):
		return self._history

	def get_when_history_updated(self):
		return self._historyUpdateTime

	def update_dnd(self):
		le = concurrent.AsyncLinearExecution(self._pool, self._update_dnd), (), {}
		self._perform_op_while_loggedin(le)

	def set_dnd(self, dnd):
		le = concurrent.AsyncLinearExecution(self._pool, self._set_dnd)
		le.start(dnd)

	def is_available(self, messageId):
		actualPath = os.path.join(self._voicemailCachePath, "%s.mp3" % messageId)
		return os.path.exists(actualPath)

	def voicemail_path(self, messageId):
		actualPath = os.path.join(self._voicemailCachePath, "%s.mp3" % messageId)
		if not os.path.exists(actualPath):
			raise RuntimeError("Voicemail not available")
		return actualPath

	def download_voicemail(self, messageId):
		le = concurrent.AsyncLinearExecution(self._pool, self._download_voicemail)
		le.start(messageId)

	def _set_dnd(self, dnd):
		oldDnd = self._dnd
		try:
			assert self.state == self.LOGGEDIN_STATE, "DND requires being logged in (currently %s" % self.state
			with qui_utils.notify_busy(self._errorLog, "Setting DND Status"):
				yield (
					self._backend[0].set_dnd,
					(dnd, ),
					{},
				)
		except Exception, e:
			_moduleLogger.exception("Reporting error to user")
			self.error.emit(str(e))
			return
		self._dnd = dnd
		if oldDnd != self._dnd:
			self.dndStateChange.emit(self._dnd)

	def get_dnd(self):
		return self._dnd

	def get_account_number(self):
		if self.state != self.LOGGEDIN_STATE:
			return ""
		return self._backend[0].get_account_number()

	def get_callback_numbers(self):
		if self.state != self.LOGGEDIN_STATE:
			return {}
		return self._backend[0].get_callback_numbers()

	def get_callback_number(self):
		return self._callback

	def set_callback_number(self, callback):
		le = concurrent.AsyncLinearExecution(self._pool, self._set_callback_number)
		le.start(callback)

	def _set_callback_number(self, callback):
		oldCallback = self._callback
		try:
			assert self.state == self.LOGGEDIN_STATE, "Callbacks configurable only when logged in (currently %s" % self.state
			yield (
				self._backend[0].set_callback_number,
				(callback, ),
				{},
			)
		except Exception, e:
			_moduleLogger.exception("Reporting error to user")
			self.error.emit(str(e))
			return
		self._callback = callback
		if oldCallback != self._callback:
			self.callbackNumberChanged.emit(self._callback)

	def _login(self, username, password):
		with qui_utils.notify_busy(self._errorLog, "Logging In"):
			self._loggedInTime = self._LOGGINGIN_TIME
			self.stateChange.emit(self.LOGGINGIN_STATE)
			finalState = self.LOGGEDOUT_STATE
			accountData = None
			try:
				if accountData is None and self._backend[0].is_quick_login_possible():
					accountData = yield (
						self._backend[0].refresh_account_info,
						(),
						{},
					)
					if accountData is not None:
						_moduleLogger.info("Logged in through cookies")
					else:
						# Force a clearing of the cookies
						yield (
							self._backend[0].logout,
							(),
							{},
						)

				if accountData is None:
					accountData = yield (
						self._backend[0].login,
						(username, password),
						{},
					)
					if accountData is not None:
						_moduleLogger.info("Logged in through credentials")

				if accountData is not None:
					self._loggedInTime = int(time.time())
					oldUsername = self._username
					self._username = username
					finalState = self.LOGGEDIN_STATE
					if oldUsername != self._username:
						needOps = not self._load()
					else:
						needOps = True

					self._voicemailCachePath = os.path.join(self._cachePath, "%s.voicemail.cache" % self._username)
					try:
						os.makedirs(self._voicemailCachePath)
					except OSError, e:
						if e.errno != 17:
							raise

					self.loggedIn.emit()
					self.stateChange.emit(finalState)
					finalState = None # Mark it as already set
					self._process_account_data(accountData)

					if needOps:
						loginOps = self._loginOps[:]
					else:
						loginOps = []
					del self._loginOps[:]
					for asyncOp, args, kwds in loginOps:
						asyncOp.start(*args, **kwds)
				else:
					self._loggedInTime = self._LOGGEDOUT_TIME
					self.error.emit("Error logging in")
			except Exception, e:
				_moduleLogger.exception("Booh")
				self._loggedInTime = self._LOGGEDOUT_TIME
				_moduleLogger.exception("Reporting error to user")
				self.error.emit(str(e))
			finally:
				if finalState is not None:
					self.stateChange.emit(finalState)
			if accountData is not None and self._callback:
				self.set_callback_number(self._callback)

	def _load(self):
		updateMessages = len(self._messages) != 0
		updateHistory = len(self._history) != 0
		oldDnd = self._dnd
		oldCallback = self._callback

		self._messages = []
		self._cleanMessages = []
		self._history = []
		self._dnd = False
		self._callback = ""

		loadedFromCache = self._load_from_cache()
		if loadedFromCache:
			updateMessages = True
			updateHistory = True

		if updateMessages:
			self.messagesUpdated.emit()
		if updateHistory:
			self.historyUpdated.emit()
		if oldDnd != self._dnd:
			self.dndStateChange.emit(self._dnd)
		if oldCallback != self._callback:
			self.callbackNumberChanged.emit(self._callback)

		return loadedFromCache

	def _load_from_cache(self):
		if self._cachePath is None:
			return False
		cachePath = os.path.join(self._cachePath, "%s.cache" % self._username)

		try:
			with open(cachePath, "rb") as f:
				dumpedData = pickle.load(f)
		except (pickle.PickleError, IOError, EOFError, ValueError, ImportError):
			_moduleLogger.exception("Pickle fun loading")
			return False
		except:
			_moduleLogger.exception("Weirdness loading")
			return False

		try:
			version, build = dumpedData[0:2]
		except ValueError:
			_moduleLogger.exception("Upgrade/downgrade fun")
			return False
		except:
			_moduleLogger.exception("Weirdlings")
			return False

		if misc_utils.compare_versions(
			self._OLDEST_COMPATIBLE_FORMAT_VERSION,
			misc_utils.parse_version(version),
		) <= 0:
			try:
				(
					version, build,
					messages, messageUpdateTime,
					history, historyUpdateTime,
					dnd, callback
				) = dumpedData
			except ValueError:
				_moduleLogger.exception("Upgrade/downgrade fun")
				return False
			except:
				_moduleLogger.exception("Weirdlings")
				return False

			_moduleLogger.info("Loaded cache")
			self._messages = messages
			self._alert_on_messages(self._messages)
			self._messageUpdateTime = messageUpdateTime
			self._history = history
			self._historyUpdateTime = historyUpdateTime
			self._dnd = dnd
			self._callback = callback
			return True
		else:
			_moduleLogger.debug(
				"Skipping cache due to version mismatch (%s-%s)" % (
					version, build
				)
			)
			return False

	def _save_to_cache(self):
		_moduleLogger.info("Saving cache")
		if self._cachePath is None:
			return
		cachePath = os.path.join(self._cachePath, "%s.cache" % self._username)

		try:
			dataToDump = (
				constants.__version__, constants.__build__,
				self._messages, self._messageUpdateTime,
				self._history, self._historyUpdateTime,
				self._dnd, self._callback
			)
			with open(cachePath, "wb") as f:
				pickle.dump(dataToDump, f, pickle.HIGHEST_PROTOCOL)
			_moduleLogger.info("Cache saved")
		except (pickle.PickleError, IOError):
			_moduleLogger.exception("While saving")

	def _clear_cache(self):
		updateMessages = len(self._messages) != 0
		updateHistory = len(self._history) != 0
		oldDnd = self._dnd
		oldCallback = self._callback

		self._messages = []
		self._messageUpdateTime = datetime.datetime(1971, 1, 1)
		self._history = []
		self._historyUpdateTime = datetime.datetime(1971, 1, 1)
		self._dnd = False
		self._callback = ""

		if updateMessages:
			self.messagesUpdated.emit()
		if updateHistory:
			self.historyUpdated.emit()
		if oldDnd != self._dnd:
			self.dndStateChange.emit(self._dnd)
		if oldCallback != self._callback:
			self.callbackNumberChanged.emit(self._callback)

		self._save_to_cache()
		self._clear_voicemail_cache()

	def _clear_voicemail_cache(self):
		import shutil
		shutil.rmtree(self._voicemailCachePath, True)

	def _update_account(self):
		try:
			assert self.state == self.LOGGEDIN_STATE, "Contacts requires being logged in (currently %s)" % self.state
			with qui_utils.notify_busy(self._errorLog, "Updating Account"):
				accountData = yield (
					self._backend[0].refresh_account_info,
					(),
					{},
				)
		except Exception, e:
			_moduleLogger.exception("Reporting error to user")
			self.error.emit(str(e))
			return
		self._process_account_data(accountData)

	def _update_messages(self, messageType):
		try:
			assert self.state == self.LOGGEDIN_STATE, "Messages requires being logged in (currently %s" % self.state
			with qui_utils.notify_busy(self._errorLog, "Updating %s Messages" % messageType):
				self._messages = yield (
					self._backend[0].get_messages,
					(messageType, ),
					{},
				)
		except Exception, e:
			_moduleLogger.exception("Reporting error to user")
			self.error.emit(str(e))
			return
		self._messageUpdateTime = datetime.datetime.now()
		self.messagesUpdated.emit()
		self._alert_on_messages(self._messages)

	def _update_history(self):
		try:
			assert self.state == self.LOGGEDIN_STATE, "History requires being logged in (currently %s" % self.state
			with qui_utils.notify_busy(self._errorLog, "Updating History"):
				self._history = yield (
					self._backend[0].get_recent,
					(),
					{},
				)
		except Exception, e:
			_moduleLogger.exception("Reporting error to user")
			self.error.emit(str(e))
			return
		self._historyUpdateTime = datetime.datetime.now()
		self.historyUpdated.emit()

	def _update_dnd(self):
		oldDnd = self._dnd
		try:
			assert self.state == self.LOGGEDIN_STATE, "DND requires being logged in (currently %s" % self.state
			self._dnd = yield (
				self._backend[0].is_dnd,
				(),
				{},
			)
		except Exception, e:
			_moduleLogger.exception("Reporting error to user")
			self.error.emit(str(e))
			return
		if oldDnd != self._dnd:
			self.dndStateChange(self._dnd)

	def _download_voicemail(self, messageId):
		actualPath = os.path.join(self._voicemailCachePath, "%s.mp3" % messageId)
		targetPath = "%s.%s.part" % (actualPath, time.time())
		if os.path.exists(actualPath):
			self.voicemailAvailable.emit(messageId, actualPath)
			return
		with qui_utils.notify_busy(self._errorLog, "Downloading Voicemail"):
			try:
				yield (
					self._backend[0].download,
					(messageId, targetPath),
					{},
				)
			except Exception, e:
				_moduleLogger.exception("Passing to user")
				self.error.emit(str(e))
				return

		if os.path.exists(actualPath):
			try:
				os.remove(targetPath)
			except:
				_moduleLogger.exception("Ignoring file problems with cache")
			self.voicemailAvailable.emit(messageId, actualPath)
			return
		else:
			os.rename(targetPath, actualPath)
			self.voicemailAvailable.emit(messageId, actualPath)

	def _perform_op_while_loggedin(self, op):
		if self.state == self.LOGGEDIN_STATE:
			op, args, kwds = op
			op.start(*args, **kwds)
		else:
			self._push_login_op(op)

	def _push_login_op(self, asyncOp):
		assert self.state != self.LOGGEDIN_STATE, "Can only queue work when logged out"
		if asyncOp in self._loginOps:
			_moduleLogger.info("Skipping queueing duplicate op: %r" % asyncOp)
			return
		self._loginOps.append(asyncOp)

	def _process_account_data(self, accountData):
		self._contacts = dict(
			(contactId, contactDetails)
			for contactId, contactDetails in accountData["contacts"].iteritems()
			# A zero contact id is the catch all for unknown contacts
			if contactId != "0"
		)

		self._accountUpdateTime = datetime.datetime.now()
		self.accountUpdated.emit()

	def _alert_on_messages(self, messages):
		cleanNewMessages = list(self._clean_messages(messages))
		cleanNewMessages.sort(key=lambda m: m["contactId"])
		if self._cleanMessages:
			if self._cleanMessages != cleanNewMessages:
				self.newMessages.emit()
		self._cleanMessages = cleanNewMessages

	def _clean_messages(self, messages):
		for message in messages:
			cleaned = dict(
				kv
				for kv in message.iteritems()
				if kv[0] not in
				[
					"relTime",
					"time",
					"isArchived",
					"isRead",
					"isSpam",
					"isTrash",
				]
			)

			# Don't let outbound messages cause alerts, especially if the package has only outbound
			cleaned["messageParts"] = [
				tuple(part[0:-1]) for part in cleaned["messageParts"] if part[0] != "Me:"
			]
			if not cleaned["messageParts"]:
				continue

			yield cleaned
