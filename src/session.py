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
		self.sendingMessage.emit()
		self.error.emit("Not Implemented")
		# self.clear()

	def call(self):
		assert len(self._contacts) == 1
		self.calling.emit()
		self.error.emit("Not Implemented")
		# self.clear()

	def cancel(self):
		self.cancelling.emit()
		self.error.emit("Not Implemented")

	def add_contact(self, contact, details):
		assert contact not in self._contacts
		self._contacts[contact] = details
		self.recipientsChanged.emit()

	def remove_contact(self, contact):
		assert contact not in self._contacts
		del self._contacts[contact]
		self.recipientsChanged.emit()

	def get_contacts(self, contact):
		return self._contacts

	def clear(self):
		self._contacts = {}
		self.recipientsChanged.emit()


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

		self._contacts = []
		self._messages = []
		self._history = []
		self._dnd = False

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
		self.error.emit("Not Implemented")

	def clear(self):
		assert self.state == self.LOGGEDOUT_STATE
		self._backend = None
		self._draft.clear()
		self._contacts = []
		self.contactsUpdated.emit()
		self._messages = []
		self.messagesUpdated.emit()
		self._history = []
		self.historyUpdated.emit()
		self._dnd = False
		self.dndStateChange.emit(self._dnd)

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
		assert self.state == self.LOGGEDIN_STATE
		self.error.emit("Not Implemented")

	def get_dnd(self):
		return self._dnd

	def get_callback_numbers(self):
		return []

	def get_callback_number(self):
		return ""

	def set_callback_number(self):
		assert self.state == self.LOGGEDIN_STATE
		self.error.emit("Not Implemented")

	def _login(self, username, password):
		self._loggedInTime = self._LOGGINGIN_TIME
		self.stateChange.emit(self.LOGGINGIN_STATE)
		finalState = self.LOGGEDOUT_STATE
		try:
			isLoggedIn = False

			if not isLoggedIn and self._backend.is_quick_login_possible():
				try:
					isLoggedIn = yield (
						self._backend.is_authed,
						(),
						{},
					)
				except Exception, e:
					self.error.emit(str(e))
					return
				if isLoggedIn:
					_moduleLogger.info("Logged in through cookies")

			if not isLoggedIn:
				try:
					isLoggedIn = yield (
						self._backend.login,
						(username, password),
						{},
					)
				except Exception, e:
					self.error.emit(str(e))
					return
				if isLoggedIn:
					_moduleLogger.info("Logged in through credentials")

			if isLoggedIn:
				self._loggedInTime = time.time()
				self._username = username
				finalState = self.LOGGEDIN_STATE
				self.loggedIn.emit()
				# if the username is the same, do nothing
				# else clear the in-memory caches and attempt to load from file-caches
				# If caches went from empty to something, fire signals
				# Fire off queued async ops
		except Exception, e:
			self.error.emit(str(e))
		finally:
			self.stateChange.emit(finalState)

	def _update_contacts(self):
		self.error.emit("Not Implemented")
		try:
			isLoggedIn = yield (
				self._backend.is_authed,
				(),
				{},
			)
		except Exception, e:
			self.error.emit(str(e))
			return

	def _update_messages(self):
		self.error.emit("Not Implemented")
		try:
			isLoggedIn = yield (
				self._backend.is_authed,
				(),
				{},
			)
		except Exception, e:
			self.error.emit(str(e))
			return

	def _update_history(self):
		self.error.emit("Not Implemented")
		try:
			isLoggedIn = yield (
				self._backend.is_authed,
				(),
				{},
			)
		except Exception, e:
			self.error.emit(str(e))
			return

	def _update_dnd(self):
		self.error.emit("Not Implemented")
		try:
			isLoggedIn = yield (
				self._backend.is_authed,
				(),
				{},
			)
		except Exception, e:
			self.error.emit(str(e))
			return

	def _perform_op_while_loggedin(self, op):
		if self.state == self.LOGGEDIN_STATE:
			op()
		else:
			self._push_login_op(op)

	def _push_login_op(self, asyncOp):
		assert self.state != self.LOGGEDIN_STATE
		if asyncOp in self._loginOps:
			_moduleLogger.info("Skipping queueing duplicate op: %r" % asyncOp)
			return
		self._loginOps.append(asyncOp)
