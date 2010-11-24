#!/usr/bin/env python

from __future__ import with_statement
from __future__ import division

import functools
import copy
import logging

from PyQt4 import QtGui
from PyQt4 import QtCore

from util import qui_utils
from util import misc as misc_utils


_moduleLogger = logging.getLogger(__name__)


class CredentialsDialog(object):

	def __init__(self, app):
		self._usernameField = QtGui.QLineEdit()
		self._passwordField = QtGui.QLineEdit()
		self._passwordField.setEchoMode(QtGui.QLineEdit.PasswordEchoOnEdit)

		self._credLayout = QtGui.QGridLayout()
		self._credLayout.addWidget(QtGui.QLabel("Username"), 0, 0)
		self._credLayout.addWidget(self._usernameField, 0, 1)
		self._credLayout.addWidget(QtGui.QLabel("Password"), 1, 0)
		self._credLayout.addWidget(self._passwordField, 1, 1)

		self._loginButton = QtGui.QPushButton("&Login")
		self._buttonLayout = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Cancel)
		self._buttonLayout.addButton(self._loginButton, QtGui.QDialogButtonBox.AcceptRole)

		self._layout = QtGui.QVBoxLayout()
		self._layout.addLayout(self._credLayout)
		self._layout.addWidget(self._buttonLayout)

		self._dialog = QtGui.QDialog()
		self._dialog.setWindowTitle("Login")
		self._dialog.setLayout(self._layout)
		self._dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
		qui_utils.set_autorient(self._dialog, True)
		self._buttonLayout.accepted.connect(self._dialog.accept)
		self._buttonLayout.rejected.connect(self._dialog.reject)

		self._closeWindowAction = QtGui.QAction(None)
		self._closeWindowAction.setText("Close")
		self._closeWindowAction.setShortcut(QtGui.QKeySequence("CTRL+w"))
		self._closeWindowAction.triggered.connect(self._on_close_window)

		self._dialog.addAction(self._closeWindowAction)
		self._dialog.addAction(app.quitAction)
		self._dialog.addAction(app.fullscreenAction)

	def run(self, defaultUsername, defaultPassword, parent=None):
		self._dialog.setParent(parent, QtCore.Qt.Dialog)
		try:
			self._usernameField.setText(defaultUsername)
			self._passwordField.setText(defaultPassword)

			response = self._dialog.exec_()
			if response == QtGui.QDialog.Accepted:
				return str(self._usernameField.text()), str(self._passwordField.text())
			elif response == QtGui.QDialog.Rejected:
				raise RuntimeError("Login Cancelled")
			else:
				raise RuntimeError("Unknown Response")
		finally:
			self._dialog.setParent(None, QtCore.Qt.Dialog)

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_close_window(self, checked = True):
		self._dialog.reject()


class AccountDialog(object):

	# @bug Can't configure callback number

	def __init__(self, app):
		self._doClear = False

		self._accountNumberLabel = QtGui.QLabel("NUMBER NOT SET")
		self._clearButton = QtGui.QPushButton("Clear Account")
		self._clearButton.clicked.connect(self._on_clear)

		self._credLayout = QtGui.QGridLayout()
		self._credLayout.addWidget(QtGui.QLabel("Account"), 0, 0)
		self._credLayout.addWidget(self._accountNumberLabel, 0, 1)
		self._credLayout.addWidget(QtGui.QLabel("Callback"), 1, 0)
		self._credLayout.addWidget(QtGui.QLabel(""), 2, 0)
		self._credLayout.addWidget(self._clearButton, 2, 1)
		self._credLayout.addWidget(QtGui.QLabel(""), 3, 0)

		self._loginButton = QtGui.QPushButton("&Apply")
		self._buttonLayout = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Cancel)
		self._buttonLayout.addButton(self._loginButton, QtGui.QDialogButtonBox.AcceptRole)

		self._layout = QtGui.QVBoxLayout()
		self._layout.addLayout(self._credLayout)
		self._layout.addWidget(self._buttonLayout)

		self._dialog = QtGui.QDialog()
		self._dialog.setWindowTitle("Login")
		self._dialog.setLayout(self._layout)
		qui_utils.set_autorient(self._dialog, True)
		self._buttonLayout.accepted.connect(self._dialog.accept)
		self._buttonLayout.rejected.connect(self._dialog.reject)

		self._closeWindowAction = QtGui.QAction(None)
		self._closeWindowAction.setText("Close")
		self._closeWindowAction.setShortcut(QtGui.QKeySequence("CTRL+w"))
		self._closeWindowAction.triggered.connect(self._on_close_window)

		self._dialog.addAction(self._closeWindowAction)
		self._dialog.addAction(app.quitAction)
		self._dialog.addAction(app.fullscreenAction)

	@property
	def doClear(self):
		return self._doClear

	accountNumber = property(
		lambda self: str(self._accountNumberLabel.text()),
		lambda self, num: self._accountNumberLabel.setText(num),
	)

	def run(self, parent=None):
		self._doClear = False
		self._dialog.setParent(parent)

		response = self._dialog.exec_()
		return response

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	def _on_clear(self, checked = False):
		self._doClear = True
		self._dialog.accept()

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_close_window(self, checked = True):
		self._dialog.reject()


class SMSEntryWindow(object):

	MAX_CHAR = 160

	def __init__(self, parent, app, session, errorLog):
		self._session = session
		self._session.draft.recipientsChanged.connect(self._on_recipients_changed)
		self._session.draft.called.connect(self._on_op_finished)
		self._session.draft.sentMessage.connect(self._on_op_finished)
		self._session.draft.cancelled.connect(self._on_op_finished)
		self._errorLog = errorLog

		self._targetLayout = QtGui.QVBoxLayout()
		self._targetList = QtGui.QWidget()
		self._targetList.setLayout(self._targetLayout)
		self._history = QtGui.QTextEdit()
		self._history.setReadOnly(True)
		self._smsEntry = QtGui.QTextEdit()
		self._smsEntry.textChanged.connect(self._on_letter_count_changed)

		self._entryLayout = QtGui.QVBoxLayout()
		self._entryLayout.addWidget(self._targetList)
		self._entryLayout.addWidget(self._history)
		self._entryLayout.addWidget(self._smsEntry)
		self._entryLayout.setContentsMargins(0, 0, 0, 0)
		self._entryWidget = QtGui.QWidget()
		self._entryWidget.setLayout(self._entryLayout)
		self._entryWidget.setContentsMargins(0, 0, 0, 0)
		self._scrollEntry = QtGui.QScrollArea()
		self._scrollEntry.setWidget(self._entryWidget)
		self._scrollEntry.setWidgetResizable(True)
		self._scrollEntry.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignBottom)
		self._scrollEntry.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
		self._scrollEntry.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

		self._characterCountLabel = QtGui.QLabel("0 (0)")
		self._singleNumberSelector = QtGui.QComboBox()
		self._smsButton = QtGui.QPushButton("SMS")
		self._smsButton.clicked.connect(self._on_sms_clicked)
		self._dialButton = QtGui.QPushButton("Dial")
		self._dialButton.clicked.connect(self._on_call_clicked)

		self._buttonLayout = QtGui.QHBoxLayout()
		self._buttonLayout.addWidget(self._characterCountLabel)
		self._buttonLayout.addWidget(self._singleNumberSelector)
		self._buttonLayout.addWidget(self._smsButton)
		self._buttonLayout.addWidget(self._dialButton)

		self._layout = QtGui.QVBoxLayout()
		self._layout.addWidget(self._scrollEntry)
		self._layout.addLayout(self._buttonLayout)

		centralWidget = QtGui.QWidget()
		centralWidget.setLayout(self._layout)

		self._window = QtGui.QMainWindow(parent)
		qui_utils.set_autorient(self._window, True)
		qui_utils.set_stackable(self._window, True)
		self._window.setWindowTitle("Contact")
		self._window.setCentralWidget(centralWidget)

		self._closeWindowAction = QtGui.QAction(None)
		self._closeWindowAction.setText("Close")
		self._closeWindowAction.setShortcut(QtGui.QKeySequence("CTRL+w"))
		self._closeWindowAction.triggered.connect(self._on_close_window)

		fileMenu = self._window.menuBar().addMenu("&File")
		fileMenu.addAction(self._closeWindowAction)
		fileMenu.addAction(app.quitAction)
		viewMenu = self._window.menuBar().addMenu("&View")
		viewMenu.addAction(app.fullscreenAction)

		self._window.show()
		self._update_recipients()

	def _update_letter_count(self):
		count = self._smsEntry.toPlainText().size()
		numTexts, numCharInText = divmod(count, self.MAX_CHAR)
		numTexts += 1
		numCharsLeftInText = self.MAX_CHAR - numCharInText
		self._characterCountLabel.setText("%d (%d)" % (numCharsLeftInText, numTexts))

	def _update_button_state(self):
		if self._session.draft.get_num_contacts() == 0:
			self._dialButton.setEnabled(False)
			self._smsButton.setEnabled(False)
		elif self._session.draft.get_num_contacts() == 1:
			count = self._smsEntry.toPlainText().size()
			if count == 0:
				self._dialButton.setEnabled(True)
				self._smsButton.setEnabled(False)
			else:
				self._dialButton.setEnabled(False)
				self._smsButton.setEnabled(True)
		else:
			self._dialButton.setEnabled(False)
			self._smsButton.setEnabled(True)

	def _update_recipients(self):
		draftContactsCount = self._session.draft.get_num_contacts()
		if draftContactsCount == 0:
			self._window.hide()
		elif draftContactsCount == 1:
			(cid, ) = self._session.draft.get_contacts()
			title = self._session.draft.get_title(cid)
			description = self._session.draft.get_description(cid)
			numbers = self._session.draft.get_numbers(cid)

			self._targetList.setVisible(False)
			if description:
				self._history.setHtml(description)
				self._history.setVisible(True)
			else:
				self._history.setHtml("")
				self._history.setVisible(False)
			self._populate_number_selector(self._singleNumberSelector, cid, numbers)

			self._scroll_to_bottom()
			self._window.setWindowTitle(title)
			self._window.show()
		else:
			self._targetList.setVisible(True)
			while self._targetLayout.count():
				removedLayoutItem = self._targetLayout.takeAt(self._targetLayout.count()-1)
				removedWidget = removedLayoutItem.widget()
				removedWidget.close()
			for cid in self._session.draft.get_contacts():
				title = self._session.draft.get_title(cid)
				description = self._session.draft.get_description(cid)
				numbers = self._session.draft.get_numbers(cid)

				titleLabel = QtGui.QLabel(title)
				numberSelector = QtGui.QComboBox()
				self._populate_number_selector(numberSelector, cid, numbers)
				deleteButton = QtGui.QPushButton("Delete")
				callback = functools.partial(
					self._on_remove_contact,
					cid
				)
				callback.__name__ = "b"
				deleteButton.clicked.connect(callback)

				rowLayout = QtGui.QHBoxLayout()
				rowLayout.addWidget(titleLabel)
				rowLayout.addWidget(numberSelector)
				rowLayout.addWidget(deleteButton)
				rowWidget = QtGui.QWidget()
				rowWidget.setLayout(rowLayout)
				self._targetLayout.addWidget(rowWidget)
			self._history.setHtml("")
			self._history.setVisible(False)
			self._singleNumberSelector.setVisible(False)

			self._scroll_to_bottom()
			self._window.setWindowTitle("Contacts")
			self._window.show()

	def _populate_number_selector(self, selector, cid, numbers):
		while 0 < selector.count():
			selector.removeItem(0)

		if len(numbers) == 1:
			numbers, defaultIndex = _get_contact_numbers(self._session, cid, numbers[0])
		else:
			defaultIndex = 0

		for number, description in numbers:
			if description:
				label = "%s - %s" % (number, description)
			else:
				label = number
			selector.addItem(label)
		selector.setVisible(True)
		if 1 < len(numbers):
			selector.setEnabled(True)
			selector.setCurrentIndex(defaultIndex)
		else:
			selector.setEnabled(False)
		callback = functools.partial(
			self._on_change_number,
			cid
		)
		callback.__name__ = "thanks partials for not having names and pyqt for requiring them"
		selector.currentIndexChanged.connect(
			QtCore.pyqtSlot(int)(callback)
		)

	def _scroll_to_bottom(self):
		self._scrollEntry.ensureWidgetVisible(self._smsEntry)

	@misc_utils.log_exception(_moduleLogger)
	def _on_sms_clicked(self, arg):
		message = str(self._smsEntry.toPlainText())
		self._session.draft.send(message)
		self._smsEntry.setPlainText("")

	@misc_utils.log_exception(_moduleLogger)
	def _on_call_clicked(self, arg):
		self._session.draft.call()
		self._smsEntry.setPlainText("")

	@misc_utils.log_exception(_moduleLogger)
	def _on_remove_contact(self, cid, toggled):
		self._session.draft.remove_contact(cid)

	@misc_utils.log_exception(_moduleLogger)
	def _on_change_number(self, cid, index):
		# Exception thrown when the first item is removed
		numbers = self._session.draft.get_numbers(cid)
		number = numbers[index][0]
		self._session.draft.set_selected_number(cid, number)

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_recipients_changed(self):
		self._update_recipients()

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_op_finished(self):
		self._window.hide()

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_letter_count_changed(self):
		self._update_letter_count()
		self._update_button_state()

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_close_window(self, checked = True):
		self._window.hide()


def _get_contact_numbers(session, contactId, numberDescription):
	contactPhoneNumbers = []
	if contactId and contactId != "0":
		try:
			contactDetails = copy.deepcopy(session.get_contacts()[contactId])
			contactPhoneNumbers = contactDetails["numbers"]
		except KeyError:
			contactPhoneNumbers = []
		contactPhoneNumbers = [
			(contactPhoneNumber["phoneNumber"], contactPhoneNumber["phoneType"])
			for contactPhoneNumber in contactPhoneNumbers
		]
		if contactPhoneNumbers:
			uglyContactNumbers = (
				misc_utils.make_ugly(contactNumber)
				for (contactNumber, _) in contactPhoneNumbers
			)
			defaultMatches = [
				misc_utils.similar_ugly_numbers(numberDescription[0], contactNumber)
				for contactNumber in uglyContactNumbers
			]
			try:
				defaultIndex = defaultMatches.index(True)
			except ValueError:
				contactPhoneNumbers.append(numberDescription)
				defaultIndex = len(contactPhoneNumbers)-1
				_moduleLogger.warn(
					"Could not find contact %r's number %s among %r" % (
						contactId, numberDescription, contactPhoneNumbers
					)
				)

	if not contactPhoneNumbers:
		contactPhoneNumbers = [numberDescription]
		defaultIndex = -1

	return contactPhoneNumbers, defaultIndex
