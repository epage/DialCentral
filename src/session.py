import os
import time
import logging

from PyQt4 import QtCore

from util import qore_utils
from util import concurrent

from backends import gv_backend


_moduleLogger = logging.getLogger(__name__)


class Draft(QtCore.QObject):

	sendingMessage = QtCore.pyqtSignal()
	sentMessage = QtCore.pyqtSignal()
	calling = QtCore.pyqtSignal()
	called = QtCore.pyqtSignal()
	cancelling = QtCore.pyqtSignal()
	cancelled = QtCore.pyqtSignal()
	error = QtCore.pyqtSignal(str)

	recipientsChanged = QtCore.pyqtSignal()

	def __init__(self, pool):
		QtCore.QObject.__init__(self)
		self._contacts = {}
		self._pool = pool

	def send(self, text):
		assert 0 < len(self._contacts)
		le = concurrent.AsyncLinearExecution(self._pool, self._send)
		le.start(text)

	def call(self):
		assert len(self._contacts) == 1
		le = concurrent.AsyncLinearExecution(self._pool, self._call)
		le.start()

	def cancel(self):
		le = concurrent.AsyncLinearExecution(self._pool, self._cancel)
		le.start()

	def add_contact(self, contactId, title, description, numbersWithDescriptions):
		assert contactId not in self._contacts
		contactDetails = title, description, numbersWithDescriptions
		self._contacts[contactId] = contactDetails
		self.recipientsChanged.emit()

	def remove_contact(self, contactId):
		assert contactId in self._contacts
		del self._contacts[contactId]
		self.recipientsChanged.emit()

	def get_contacts(self):
		return self._contacts

	def clear(self):
		self._contacts = {}
		self.recipientsChanged.emit()

	def _send(self, text):
		self.sendingMessage.emit()
		try:
			self.error.emit("Not Implemented")
			self.sentMessage.emit()
			self.clear()
		except Exception, e:
			self.error.emit(str(e))

	def _call(self):
		self.calling.emit()
		try:
			self.error.emit("Not Implemented")
			self.called.emit()
			self.clear()
		except Exception, e:
			self.error.emit(str(e))

	def _cancel(self):
		self.cancelling.emit()
		try:
			yield (
				self._backend.cancel,
				(),
				{},
			)
			self.cancelled.emit()
		except Exception, e:
			self.error.emit(str(e))


class Session(QtCore.QObject):

	stateChange = QtCore.pyqtSignal(str)
	loggedOut = QtCore.pyqtSignal()
	loggedIn = QtCore.pyqtSignal()
	callbackNumberChanged = QtCore.pyqtSignal(str)

	contactsUpdated = QtCore.pyqtSignal()
	messagesUpdated = QtCore.pyqtSignal()
	historyUpdated = QtCore.pyqtSignal()
	dndStateChange = QtCore.pyqtSignal(bool)

	error = QtCore.pyqtSignal(str)

	LOGGEDOUT_STATE = "logged out"
	LOGGINGIN_STATE = "logging in"
	LOGGEDIN_STATE = "logged in"

	_LOGGEDOUT_TIME = -1
	_LOGGINGIN_TIME = 0

	def __init__(self, cachePath = None):
		QtCore.QObject.__init__(self)
		self._pool = qore_utils.AsyncPool()
		self._backend = None
		self._loggedInTime = self._LOGGEDOUT_TIME
		self._loginOps = []
		self._cachePath = cachePath
		self._username = None
		self._draft = Draft(self._pool)

		self._contacts = {}
		self._messages = []
		self._history = []
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
		assert self.state == self.LOGGEDOUT_STATE
		assert username != ""
		if self._cachePath is not None:
			cookiePath = os.path.join(self._cachePath, "%s.cookies" % username)
		else:
			cookiePath = None

		if self._username != username or self._backend is None:
			self._backend = gv_backend.GVDialer(cookiePath)

		self._pool.start()
		le = concurrent.AsyncLinearExecution(self._pool, self._login)
		le.start(username, password)

	def logout(self):
		assert self.state != self.LOGGEDOUT_STATE
		self._pool.stop()
		self._loggedInTime = self._LOGGEDOUT_TIME
		self._backend.persist()
		self._save_to_cache()

	def clear(self):
		assert self.state == self.LOGGEDOUT_STATE
		self._backend.logout()
		self._backend = None
		self._clear_cache()
		self._draft.clear()

	def logout_and_clear(self):
		assert self.state != self.LOGGEDOUT_STATE
		self._pool.stop()
		self._loggedInTime = self._LOGGEDOUT_TIME
		self.clear()

	def update_contacts(self):
		le = concurrent.AsyncLinearExecution(self._pool, self._update_contacts)
		self._perform_op_while_loggedin(le)

	def get_contacts(self):
		return self._contacts

	def update_messages(self):
		le = concurrent.AsyncLinearExecution(self._pool, self._update_messages)
		self._perform_op_while_loggedin(le)

	def get_messages(self):
		return self._messages

	def update_history(self):
		le = concurrent.AsyncLinearExecution(self._pool, self._update_history)
		self._perform_op_while_loggedin(le)

	def get_history(self):
		return self._history

	def update_dnd(self):
		le = concurrent.AsyncLinearExecution(self._pool, self._update_dnd)
		self._perform_op_while_loggedin(le)

	def set_dnd(self, dnd):
		# I'm paranoid about our state geting out of sync so we set no matter
		# what but act as if we have the cannonical state
		assert self.state == self.LOGGEDIN_STATE
		oldDnd = self._dnd
		try:
			yield (
				self._backend.set_dnd,
				(dnd),
				{},
			)
		except Exception, e:
			self.error.emit(str(e))
			return
		self._dnd = dnd
		if oldDnd != self._dnd:
			self.dndStateChange.emit(self._dnd)

	def get_dnd(self):
		return self._dnd

	def get_callback_numbers(self):
		# @todo Remove evilness
		return self._backend.get_callback_numbers()

	def get_callback_number(self):
		return self._callback

	def set_callback_number(self, callback):
		# I'm paranoid about our state geting out of sync so we set no matter
		# what but act as if we have the cannonical state
		assert self.state == self.LOGGEDIN_STATE
		oldCallback = self._callback
		try:
			yield (
				self._backend.set_callback_number,
				(callback),
				{},
			)
		except Exception, e:
			self.error.emit(str(e))
			return
		self._callback = callback
		if oldCallback != self._callback:
			self.callbackNumberChanged.emit(self._callback)

	def _login(self, username, password):
		self._loggedInTime = self._LOGGINGIN_TIME
		self.stateChange.emit(self.LOGGINGIN_STATE)
		finalState = self.LOGGEDOUT_STATE
		try:
			isLoggedIn = False

			if not isLoggedIn and self._backend.is_quick_login_possible():
				isLoggedIn = yield (
					self._backend.is_authed,
					(),
					{},
				)
				if isLoggedIn:
					_moduleLogger.info("Logged in through cookies")
				else:
					# Force a clearing of the cookies
					yield (
						self._backend.logout,
						(),
						{},
					)

			if not isLoggedIn:
				isLoggedIn = yield (
					self._backend.login,
					(username, password),
					{},
				)
				if isLoggedIn:
					_moduleLogger.info("Logged in through credentials")

			if isLoggedIn:
				self._loggedInTime = int(time.time())
				oldUsername = self._username
				self._username = username
				finalState = self.LOGGEDIN_STATE
				self.loggedIn.emit()
				if oldUsername != self._username:
					self._load_from_cache()
				loginOps = self._loginOps[:]
				del self._loginOps[:]
				for asyncOp in loginOps:
					asyncOp.start()
		except Exception, e:
			self.error.emit(str(e))
		finally:
			self.stateChange.emit(finalState)

	def _load_from_cache(self):
		updateContacts = len(self._contacts) != 0
		updateMessages = len(self._messages) != 0
		updateHistory = len(self._history) != 0
		oldDnd = self._dnd
		oldCallback = self._callback

		self._contacts = {}
		self._messages = []
		self._history = []
		self._dnd = False
		self._callback = ""

		if updateContacts:
			self.contactsUpdated.emit()
		if updateMessages:
			self.messagesUpdated.emit()
		if updateHistory:
			self.historyUpdated.emit()
		if oldDnd != self._dnd:
			self.dndStateChange.emit(self._dnd)
		if oldCallback != self._callback:
			self.callbackNumberChanged.emit(self._callback)

	def _save_to_cache(self):
		# @todo
		pass

	def _clear_cache(self):
		updateContacts = len(self._contacts) != 0
		updateMessages = len(self._messages) != 0
		updateHistory = len(self._history) != 0
		oldDnd = self._dnd
		oldCallback = self._callback

		self._contacts = {}
		self._messages = []
		self._history = []
		self._dnd = False
		self._callback = ""

		if updateContacts:
			self.contactsUpdated.emit()
		if updateMessages:
			self.messagesUpdated.emit()
		if updateHistory:
			self.historyUpdated.emit()
		if oldDnd != self._dnd:
			self.dndStateChange.emit(self._dnd)
		if oldCallback != self._callback:
			self.callbackNumberChanged.emit(self._callback)

		self._save_to_cache()

	def _update_contacts(self):
		try:
			self._contacts = yield (
				self._backend.get_contacts,
				(),
				{},
			)
		except Exception, e:
			self.error.emit(str(e))
			return
		self.contactsUpdated.emit()

	def _update_messages(self):
		try:
			self._messages = yield (
				self._backend.get_messages,
				(),
				{},
			)
		except Exception, e:
			self.error.emit(str(e))
			return
		self.messagesUpdated.emit()

	def _update_history(self):
		try:
			self._history = yield (
				self._backend.get_recent,
				(),
				{},
			)
		except Exception, e:
			self.error.emit(str(e))
			return
		self.historyUpdated.emit()

	def _update_dnd(self):
		oldDnd = self._dnd
		try:
			self._dnd = yield (
				self._backend.is_dnd,
				(),
				{},
			)
		except Exception, e:
			self.error.emit(str(e))
			return
		if oldDnd != self._dnd:
			self.dndStateChange(self._dnd)

	def _perform_op_while_loggedin(self, op):
		if self.state == self.LOGGEDIN_STATE:
			op.start()
		else:
			self._push_login_op(op)

	def _push_login_op(self, asyncOp):
		assert self.state != self.LOGGEDIN_STATE
		if asyncOp in self._loginOps:
			_moduleLogger.info("Skipping queueing duplicate op: %r" % asyncOp)
			return
		self._loginOps.append(asyncOp)
