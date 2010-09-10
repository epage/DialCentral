import os
import logging

from PyQt4 import QtCore


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

	def __init__(self):
		self._contacts = []

	def send(self, text):
		assert 0 < len(self._contacts)
		self.sendingMessage.emit()
		self.error.emit("Not Implemented")
		# self.clear()

	def call(self):
		assert 0 < len(self._contacts)
		self.calling.emit()
		self.error.emit("Not Implemented")
		# self.clear()

	def cancel(self):
		self.cancelling.emit()
		self.error.emit("Not Implemented")

	def add_contact(self, contact):
		assert contact not in self._contacts
		self._contacts.append(contact)
		self.recipientsChanged.emit()

	def remove_contact(self, contact):
		assert contact not in self._contacts
		self._contacts.remove(contact)
		self.recipientsChanged.emit()

	def get_contacts(self, contact):
		return self._contacts

	def clear(self):
		self._contacts = []
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
	_LOGGINGING_TIME = 0

	def __init__(self, cachePath = None):
		QtCore.QObject.__init__(self)
		self._loggedInTime = self._LOGGEDOUT_TIME
		self._loginOps = []
		self._cachePath = cachePath
		self._username = None
		self._draft = Draft()

		self._contacts = []
		self._messages = []
		self._history = []
		self._dnd = False

	@property
	def state(self):
		return {
			self._LOGGEDOUT_TIME: self.LOGGEDOUT_STATE,
			self._LOGGINGIN_TIME: self.LOGGINGIN_STATE,
		}.get(self._loggedInTime, default=self.LOGGEDIN_STATE)

	@property
	def draft(self):
		return self._draft

	def login(self, username, password):
		assert self.state == self.LOGGEDOUT_STATE
		if self._cachePath is not None:
			cookiePath = os.path.join(self._cachePath, "%s.cookies" % username)
		else:
			cookiePath = None

		self.error.emit("Not Implemented")

		# if the username is the same, do nothing
		# else clear the in-memory caches and attempt to load from file-caches
		# If caches went from empty to something, fire signals

	def logout(self):
		assert self.state != self.LOGGEDOUT_STATE
		self.error.emit("Not Implemented")

	def clear(self):
		assert self.state == self.LOGGEDOUT_STATE
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
		self._perform_op_while_loggedin(self._update_contacts)

	def get_contacts(self):
		return self._contacts

	def update_messages(self):
		self._perform_op_while_loggedin(self._update_messages)

	def get_messages(self):
		return self._messages

	def update_history(self):
		self._perform_op_while_loggedin(self._update_history)

	def get_history(self):
		return self._history

	def update_dnd(self):
		self._perform_op_while_loggedin(self._update_dnd)

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

	def _update_contacts(self):
		self.error.emit("Not Implemented")

	def _update_messages(self):
		self.error.emit("Not Implemented")

	def _update_history(self):
		self.error.emit("Not Implemented")

	def _update_dnd(self):
		self.error.emit("Not Implemented")

	def _perform_op_while_loggedin(self, op):
		if self.state == self.LOGGEDIN_STATE:
			op()
		else:
			self._push_login_op(op)

	def _push_login_op(self, op):
		assert self.state != self.LOGGEDIN_STATE
		if op in self._loginOps:
			_moduleLogger.info("Skipping queueing duplicate op: %r" % op)
			return
		self._loginOps.append(op)
