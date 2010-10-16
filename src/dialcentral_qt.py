#!/usr/bin/env python
# -*- coding: UTF8 -*-

from __future__ import with_statement

import sys
import os
import shutil
import simplejson
import re
import functools
import logging

from PyQt4 import QtGui
from PyQt4 import QtCore

import constants
from util import qui_utils
from util import qtpie
from util import misc as misc_utils

import backends.null_backend as null_backend
import backends.file_backend as file_backend
import session


_moduleLogger = logging.getLogger(__name__)


IS_MAEMO = True


class Dialcentral(object):

	_DATA_PATHS = [
		os.path.dirname(__file__),
		os.path.join(os.path.dirname(__file__), "../data"),
		os.path.join(os.path.dirname(__file__), "../lib"),
		'/usr/share/%s' % constants.__app_name__,
		'/usr/lib/%s' % constants.__app_name__,
	]

	def __init__(self, app):
		self._app = app
		self._recent = []
		self._hiddenCategories = set()
		self._hiddenUnits = {}
		self._clipboard = QtGui.QApplication.clipboard()

		self._mainWindow = None

		self._fullscreenAction = QtGui.QAction(None)
		self._fullscreenAction.setText("Fullscreen")
		self._fullscreenAction.setCheckable(True)
		self._fullscreenAction.setShortcut(QtGui.QKeySequence("CTRL+Enter"))
		self._fullscreenAction.toggled.connect(self._on_toggle_fullscreen)

		self._logAction = QtGui.QAction(None)
		self._logAction.setText("Log")
		self._logAction.setShortcut(QtGui.QKeySequence("CTRL+l"))
		self._logAction.triggered.connect(self._on_log)

		self._quitAction = QtGui.QAction(None)
		self._quitAction.setText("Quit")
		self._quitAction.setShortcut(QtGui.QKeySequence("CTRL+q"))
		self._quitAction.triggered.connect(self._on_quit)

		self._app.lastWindowClosed.connect(self._on_app_quit)
		self.load_settings()

		self._mainWindow = MainWindow(None, self)
		self._mainWindow.window.destroyed.connect(self._on_child_close)

	def load_settings(self):
		try:
			with open(constants._user_settings_, "r") as settingsFile:
				settings = simplejson.load(settingsFile)
		except IOError, e:
			_moduleLogger.info("No settings")
			settings = {}
		except ValueError:
			_moduleLogger.info("Settings were corrupt")
			settings = {}

		self._fullscreenAction.setChecked(settings.get("isFullScreen", False))

	def save_settings(self):
		settings = {
			"isFullScreen": self._fullscreenAction.isChecked(),
		}
		with open(constants._user_settings_, "w") as settingsFile:
			simplejson.dump(settings, settingsFile)
		self._mainWindow.destroy()

	@property
	def fsContactsPath(self):
		return os.path.join(constants._data_path_, "contacts")

	@property
	def fullscreenAction(self):
		return self._fullscreenAction

	@property
	def logAction(self):
		return self._logAction

	@property
	def quitAction(self):
		return self._quitAction

	def _close_windows(self):
		if self._mainWindow is not None:
			self._mainWindow.window.destroyed.disconnect(self._on_child_close)
			self._mainWindow.close()
			self._mainWindow = None

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_app_quit(self, checked = False):
		self.save_settings()

	@QtCore.pyqtSlot(QtCore.QObject)
	@misc_utils.log_exception(_moduleLogger)
	def _on_child_close(self, obj = None):
		self._mainWindow = None

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_toggle_fullscreen(self, checked = False):
		for window in self._walk_children():
			window.set_fullscreen(checked)

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_log(self, checked = False):
		with open(constants._user_logpath_, "r") as f:
			logLines = f.xreadlines()
			log = "".join(logLines)
			self._clipboard.setText(log)

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_quit(self, checked = False):
		self._close_windows()


class CredentialsDialog(object):

	def __init__(self):
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
		finally:
			self._dialog.setParent(None, QtCore.Qt.Dialog)


class AccountDialog(object):

	def __init__(self):
		self._accountNumberLabel = QtGui.QLabel("NUMBER NOT SET")
		self._clearButton = QtGui.QPushButton("Clear Account")
		self._clearButton.clicked.connect(self._on_clear)
		self._doClear = False

		self._credLayout = QtGui.QGridLayout()
		self._credLayout.addWidget(QtGui.QLabel("Account"), 0, 0)
		self._credLayout.addWidget(self._accountNumberLabel, 0, 1)
		self._credLayout.addWidget(QtGui.QLabel("Callback"), 1, 0)
		self._credLayout.addWidget(self._clearButton, 2, 1)

		self._loginButton = QtGui.QPushButton("&Login")
		self._buttonLayout = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Cancel)
		self._buttonLayout.addButton(self._loginButton, QtGui.QDialogButtonBox.AcceptRole)

		self._layout = QtGui.QVBoxLayout()
		self._layout.addLayout(self._credLayout)
		self._layout.addLayout(self._buttonLayout)

		self._dialog = QtGui.QDialog()
		self._dialog.setWindowTitle("Login")
		self._dialog.setLayout(self._layout)
		qui_utils.set_autorient(self._dialog, True)
		self._buttonLayout.accepted.connect(self._dialog.accept)
		self._buttonLayout.rejected.connect(self._dialog.reject)

	@property
	def doClear(self):
		return self._doClear

	accountNumber = property(
		lambda self: str(self._accountNumberLabel.text()),
		lambda self, num: self._accountNumberLabel.setText(num),
	)

	def run(self, defaultUsername, defaultPassword, parent=None):
		self._doClear = False
		self._dialog.setParent(parent)
		self._usernameField.setText(defaultUsername)
		self._passwordField.setText(defaultPassword)

		response = self._dialog.exec_()
		if response == QtGui.QDialog.Accepted:
			return str(self._usernameField.text()), str(self._passwordField.text())
		elif response == QtGui.QDialog.Rejected:
			raise RuntimeError("Login Cancelled")

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	def _on_clear(self, checked = False):
		self._doClear = True
		self._dialog.accept()


class SMSEntryWindow(object):

	def __init__(self, parent, app, session, errorLog):
		self._contacts = []
		self._app = app
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
		self._smsEntry = QtGui.QTextEdit()
		self._smsEntry.textChanged.connect(self._on_letter_count_changed)

		self._entryLayout = QtGui.QVBoxLayout()
		self._entryLayout.addWidget(self._targetList)
		self._entryLayout.addWidget(self._history)
		self._entryLayout.addWidget(self._smsEntry)
		self._entryWidget = QtGui.QWidget()
		self._entryWidget.setLayout(self._entryLayout)
		self._scrollEntry = QtGui.QScrollArea()
		self._scrollEntry.setWidget(self._entryWidget)
		self._scrollEntry.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignBottom)
		self._scrollEntry.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
		self._scrollEntry.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

		self._characterCountLabel = QtGui.QLabel("Letters: %s" % 0)
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
		self._window.show()
		self._update_recipients()

	def _update_letter_count(self):
		count = self._smsEntry.toPlainText().size()
		self._characterCountLabel.setText("Letters: %s" % count)

	def _update_button_state(self):
		if len(self._contacts) == 0:
			self._dialButton.setEnabled(False)
			self._smsButton.setEnabled(False)
		elif len(self._contacts) == 1:
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
				deleteButton.clicked.connect(
					QtCore.pyqtSlot()(callback)
				)

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
		for number, description in numbers:
			if description:
				label = "%s - %s" % (number, description)
			else:
				label = number
			selector.addItem(label)
		selector.setVisible(True)
		if 1 < len(numbers):
			selector.setEnabled(True)
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

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_sms_clicked(self):
		message = str(self._smsEntry.toPlainText())
		self._session.draft.send(message)
		self._smsEntry.setPlainText("")

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_call_clicked(self):
		self._session.draft.call()
		self._smsEntry.setPlainText("")

	@misc_utils.log_exception(_moduleLogger)
	def _on_remove_contact(self, cid):
		self._session.draft.remove_contact(cid)

	@misc_utils.log_exception(_moduleLogger)
	def _on_change_number(self, cid, index):
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


class DelayedWidget(object):

	def __init__(self, app):
		self._layout = QtGui.QVBoxLayout()
		self._widget = QtGui.QWidget()
		self._widget.setLayout(self._layout)

		self._child = None
		self._isEnabled = True

	@property
	def toplevel(self):
		return self._widget

	def has_child(self):
		return self._child is not None

	def set_child(self, child):
		if self._child is not None:
			self._layout.removeWidget(self._child.toplevel)
		self._child = child
		if self._child is not None:
			self._layout.addWidget(self._child.toplevel)

		if self._isEnabled:
			self._child.enable()
		else:
			self._child.disable()

	def enable(self):
		self._isEnabled = True
		if self._child is not None:
			self._child.enable()

	def disable(self):
		self._isEnabled = False
		if self._child is not None:
			self._child.disable()

	def clear(self):
		if self._child is not None:
			self._child.clear()

	def refresh(self, force=True):
		if self._child is not None:
			self._child.refresh(force)


class Dialpad(object):

	def __init__(self, app, session, errorLog):
		self._app = app
		self._session = session
		self._errorLog = errorLog

		self._plus = self._generate_key_button("+", "")
		self._entry = QtGui.QLineEdit()

		backAction = QtGui.QAction(None)
		backAction.setText("Back")
		backAction.triggered.connect(self._on_backspace)
		backPieItem = qtpie.QActionPieItem(backAction)
		clearAction = QtGui.QAction(None)
		clearAction.setText("Clear")
		clearAction.triggered.connect(self._on_clear_text)
		clearPieItem = qtpie.QActionPieItem(clearAction)
		self._back = qtpie.QPieButton(backPieItem)
		self._back.set_center(backPieItem)
		self._back.insertItem(qtpie.PieFiling.NULL_CENTER)
		self._back.insertItem(clearPieItem)
		self._back.insertItem(qtpie.PieFiling.NULL_CENTER)
		self._back.insertItem(qtpie.PieFiling.NULL_CENTER)

		self._entryLayout = QtGui.QHBoxLayout()
		self._entryLayout.addWidget(self._plus, 0, QtCore.Qt.AlignCenter)
		self._entryLayout.addWidget(self._entry, 10)
		self._entryLayout.addWidget(self._back, 0, QtCore.Qt.AlignCenter)

		self._smsButton = QtGui.QPushButton("SMS")
		self._smsButton.clicked.connect(self._on_sms_clicked)
		self._callButton = QtGui.QPushButton("Call")
		self._callButton.clicked.connect(self._on_call_clicked)

		self._padLayout = QtGui.QGridLayout()
		rows = [0, 0, 0, 1, 1, 1, 2, 2, 2]
		columns = [0, 1, 2] * 3
		keys = [
			("1", ""),
			("2", "ABC"),
			("3", "DEF"),
			("4", "GHI"),
			("5", "JKL"),
			("6", "MNO"),
			("7", "PQRS"),
			("8", "TUV"),
			("9", "WXYZ"),
		]
		for (num, letters), (row, column) in zip(keys, zip(rows, columns)):
			self._padLayout.addWidget(
				self._generate_key_button(num, letters), row, column, QtCore.Qt.AlignCenter
			)
		self._padLayout.addWidget(self._smsButton, 3, 0)
		self._padLayout.addWidget(
			self._generate_key_button("0", ""), 3, 1, QtCore.Qt.AlignCenter
		)
		self._padLayout.addWidget(self._callButton, 3, 2)

		self._layout = QtGui.QVBoxLayout()
		self._layout.addLayout(self._entryLayout)
		self._layout.addLayout(self._padLayout)
		self._widget = QtGui.QWidget()
		self._widget.setLayout(self._layout)

	@property
	def toplevel(self):
		return self._widget

	def enable(self):
		self._smsButton.setEnabled(True)
		self._callButton.setEnabled(True)

	def disable(self):
		self._smsButton.setEnabled(False)
		self._callButton.setEnabled(False)

	def clear(self):
		pass

	def refresh(self, force = True):
		pass

	def _generate_key_button(self, center, letters):
		centerPieItem = self._generate_button_slice(center)
		button = qtpie.QPieButton(centerPieItem)
		button.set_center(centerPieItem)

		if len(letters) == 0:
			for i in xrange(8):
				pieItem = qtpie.PieFiling.NULL_CENTER
				button.insertItem(pieItem)
		elif len(letters) in [3, 4]:
			for i in xrange(6 - len(letters)):
				pieItem = qtpie.PieFiling.NULL_CENTER
				button.insertItem(pieItem)

			for letter in letters:
				pieItem = self._generate_button_slice(letter)
				button.insertItem(pieItem)

			for i in xrange(2):
				pieItem = qtpie.PieFiling.NULL_CENTER
				button.insertItem(pieItem)
		else:
			raise NotImplementedError("Cannot handle %r" % letters)
		return button

	def _generate_button_slice(self, letter):
		action = QtGui.QAction(None)
		action.setText(letter)
		action.triggered.connect(lambda: self._on_keypress(letter))
		pieItem = qtpie.QActionPieItem(action)
		return pieItem

	@misc_utils.log_exception(_moduleLogger)
	def _on_keypress(self, key):
		self._entry.insert(key)

	@misc_utils.log_exception(_moduleLogger)
	def _on_backspace(self, toggled = False):
		self._entry.backspace()

	@misc_utils.log_exception(_moduleLogger)
	def _on_clear_text(self, toggled = False):
		self._entry.clear()

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_sms_clicked(self, checked = False):
		number = str(self._entry.text())
		self._entry.clear()

		contactId = number
		title = number
		description = number
		numbersWithDescriptions = [(number, "")]
		self._session.draft.add_contact(contactId, title, description, numbersWithDescriptions)

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_call_clicked(self, checked = False):
		number = str(self._entry.text())
		self._entry.clear()

		contactId = number
		title = number
		description = number
		numbersWithDescriptions = [(number, "")]
		self._session.draft.clear()
		self._session.draft.add_contact(contactId, title, description, numbersWithDescriptions)
		self._session.draft.call()


class History(object):

	DATE_IDX = 0
	ACTION_IDX = 1
	NUMBER_IDX = 2
	FROM_IDX = 3
	MAX_IDX = 4

	HISTORY_ITEM_TYPES = ["Received", "Missed", "Placed", "All"]
	HISTORY_COLUMNS = ["When", "What", "Number", "From"]
	assert len(HISTORY_COLUMNS) == MAX_IDX

	def __init__(self, app, session, errorLog):
		self._selectedFilter = self.HISTORY_ITEM_TYPES[-1]
		self._app = app
		self._session = session
		self._session.historyUpdated.connect(self._on_history_updated)
		self._errorLog = errorLog

		self._typeSelection = QtGui.QComboBox()
		self._typeSelection.addItems(self.HISTORY_ITEM_TYPES)
		self._typeSelection.setCurrentIndex(
			self.HISTORY_ITEM_TYPES.index(self._selectedFilter)
		)
		self._typeSelection.currentIndexChanged[str].connect(self._on_filter_changed)

		self._itemStore = QtGui.QStandardItemModel()
		self._itemStore.setHorizontalHeaderLabels(self.HISTORY_COLUMNS)

		self._itemView = QtGui.QTreeView()
		self._itemView.setModel(self._itemStore)
		self._itemView.setUniformRowHeights(True)
		self._itemView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self._itemView.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
		self._itemView.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
		self._itemView.setHeaderHidden(True)
		self._itemView.activated.connect(self._on_row_activated)

		self._layout = QtGui.QVBoxLayout()
		self._layout.addWidget(self._typeSelection)
		self._layout.addWidget(self._itemView)
		self._widget = QtGui.QWidget()
		self._widget.setLayout(self._layout)

		self._populate_items()

	@property
	def toplevel(self):
		return self._widget

	def enable(self):
		self._itemView.setEnabled(True)

	def disable(self):
		self._itemView.setEnabled(False)

	def clear(self):
		self._itemView.clear()

	def refresh(self, force=True):
		self._session.update_history(force)

	def _populate_items(self):
		self._itemStore.clear()
		history = self._session.get_history()
		history.sort(key=lambda item: item["time"], reverse=True)
		for event in history:
			if self._selectedFilter in [self.HISTORY_ITEM_TYPES[-1], event["action"]]:
				relTime = abbrev_relative_date(event["relTime"])
				action = event["action"]
				number = event["number"]
				prettyNumber = make_pretty(number)
				name = event["name"]
				if not name or name == number:
					name = event["location"]
				if not name:
					name = "Unknown"

				timeItem = QtGui.QStandardItem(relTime)
				actionItem = QtGui.QStandardItem(action)
				numberItem = QtGui.QStandardItem(prettyNumber)
				nameItem = QtGui.QStandardItem(name)
				row = timeItem, actionItem, numberItem, nameItem
				for item in row:
					item.setEditable(False)
					item.setCheckable(False)
					if item is not nameItem:
						itemFont = item.font()
						itemFont.setPointSize(max(itemFont.pointSize() - 3, 5))
						item.setFont(itemFont)
				numberItem.setData(event)
				self._itemStore.appendRow(row)

	@QtCore.pyqtSlot(str)
	@misc_utils.log_exception(_moduleLogger)
	def _on_filter_changed(self, newItem):
		self._selectedFilter = str(newItem)
		self._populate_items()

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_history_updated(self):
		self._populate_items()

	@QtCore.pyqtSlot(QtCore.QModelIndex)
	@misc_utils.log_exception(_moduleLogger)
	def _on_row_activated(self, index):
		rowIndex = index.row()
		item = self._itemStore.item(rowIndex, self.NUMBER_IDX)
		contactDetails = item.data().toPyObject()

		title = str(self._itemStore.item(rowIndex, self.FROM_IDX).text())
		number = str(contactDetails[QtCore.QString("number")])
		contactId = number # ids don't seem too unique so using numbers

		descriptionRows = []
		# @bug doesn't seem to print multiple entries
		for i in xrange(self._itemStore.rowCount()):
			iItem = self._itemStore.item(i, self.NUMBER_IDX)
			iContactDetails = iItem.data().toPyObject()
			iNumber = str(iContactDetails[QtCore.QString("number")])
			if number != iNumber:
				continue
			relTime = abbrev_relative_date(iContactDetails[QtCore.QString("relTime")])
			action = str(iContactDetails[QtCore.QString("action")])
			number = str(iContactDetails[QtCore.QString("number")])
			prettyNumber = make_pretty(number)
			rowItems = relTime, action, prettyNumber
			descriptionRows.append("<tr><td>%s</td></tr>" % "</td><td>".join(rowItems))
		description = "<table>%s</table>" % "".join(descriptionRows)
		numbersWithDescriptions = [(str(contactDetails[QtCore.QString("number")]), "")]
		self._session.draft.add_contact(contactId, title, description, numbersWithDescriptions)


class Messages(object):

	NO_MESSAGES = "None"
	VOICEMAIL_MESSAGES = "Voicemail"
	TEXT_MESSAGES = "SMS"
	ALL_TYPES = "All Messages"
	MESSAGE_TYPES = [NO_MESSAGES, VOICEMAIL_MESSAGES, TEXT_MESSAGES, ALL_TYPES]

	UNREAD_STATUS = "Unread"
	UNARCHIVED_STATUS = "Inbox"
	ALL_STATUS = "Any"
	MESSAGE_STATUSES = [UNREAD_STATUS, UNARCHIVED_STATUS, ALL_STATUS]

	_MIN_MESSAGES_SHOWN = 4

	def __init__(self, app, session, errorLog):
		self._selectedTypeFilter = self.ALL_TYPES
		self._selectedStatusFilter = self.ALL_STATUS
		self._app = app
		self._session = session
		self._session.messagesUpdated.connect(self._on_messages_updated)
		self._errorLog = errorLog

		self._typeSelection = QtGui.QComboBox()
		self._typeSelection.addItems(self.MESSAGE_TYPES)
		self._typeSelection.setCurrentIndex(
			self.MESSAGE_TYPES.index(self._selectedTypeFilter)
		)
		self._typeSelection.currentIndexChanged[str].connect(self._on_type_filter_changed)

		self._statusSelection = QtGui.QComboBox()
		self._statusSelection.addItems(self.MESSAGE_STATUSES)
		self._statusSelection.setCurrentIndex(
			self.MESSAGE_STATUSES.index(self._selectedStatusFilter)
		)
		self._statusSelection.currentIndexChanged[str].connect(self._on_status_filter_changed)

		self._selectionLayout = QtGui.QHBoxLayout()
		self._selectionLayout.addWidget(self._typeSelection)
		self._selectionLayout.addWidget(self._statusSelection)

		self._itemStore = QtGui.QStandardItemModel()
		self._itemStore.setHorizontalHeaderLabels(["Messages"])

		self._htmlDelegate = qui_utils.QHtmlDelegate()
		self._itemView = QtGui.QTreeView()
		self._itemView.setModel(self._itemStore)
		self._itemView.setUniformRowHeights(False)
		self._itemView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self._itemView.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
		self._itemView.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
		self._itemView.setHeaderHidden(True)
		self._itemView.setItemDelegate(self._htmlDelegate)
		self._itemView.activated.connect(self._on_row_activated)

		self._layout = QtGui.QVBoxLayout()
		self._layout.addLayout(self._selectionLayout)
		self._layout.addWidget(self._itemView)
		self._widget = QtGui.QWidget()
		self._widget.setLayout(self._layout)

		self._populate_items()

	@property
	def toplevel(self):
		return self._widget

	def enable(self):
		self._itemView.setEnabled(True)

	def disable(self):
		self._itemView.setEnabled(False)

	def clear(self):
		self._itemView.clear()

	def refresh(self, force=True):
		self._session.update_messages(force)

	def _populate_items(self):
		self._itemStore.clear()
		rawMessages = self._session.get_messages()
		rawMessages.sort(key=lambda item: item["time"], reverse=True)
		for item in rawMessages:
			isUnarchived = not item["isArchived"]
			isUnread = not item["isRead"]
			visibleStatus = {
				self.UNREAD_STATUS: isUnarchived and isUnread,
				self.UNARCHIVED_STATUS: isUnarchived,
				self.ALL_STATUS: True,
			}[self._selectedStatusFilter]

			visibleType = self._selectedTypeFilter in [item["type"], self.ALL_TYPES]
			if visibleType and visibleStatus:
				relTime = abbrev_relative_date(item["relTime"])
				number = item["number"]
				prettyNumber = make_pretty(number)
				name = item["name"]
				if not name or name == number:
					name = item["location"]
				if not name:
					name = "Unknown"

				messageParts = list(item["messageParts"])
				if len(messageParts) == 0:
					messages = ("No Transcription", )
				elif len(messageParts) == 1:
					if messageParts[0][1]:
						messages = (messageParts[0][1], )
					else:
						messages = ("No Transcription", )
				else:
					messages = [
						"<b>%s</b>: %s" % (messagePart[0], messagePart[1])
						for messagePart in messageParts
					]

				firstMessage = "<b>%s - %s</b> <i>(%s)</i>" % (name, prettyNumber, relTime)

				expandedMessages = [firstMessage]
				expandedMessages.extend(messages)
				if (self._MIN_MESSAGES_SHOWN + 1) < len(messages):
					secondMessage = "<i>%d Messages Hidden...</i>" % (len(messages) - self._MIN_MESSAGES_SHOWN, )
					collapsedMessages = [firstMessage, secondMessage]
					collapsedMessages.extend(messages[-(self._MIN_MESSAGES_SHOWN+0):])
				else:
					collapsedMessages = expandedMessages

				item = dict(item.iteritems())
				item["collapsedMessages"] = "<br/>\n".join(collapsedMessages)
				item["expandedMessages"] = "<br/>\n".join(expandedMessages)

				messageItem = QtGui.QStandardItem(item["collapsedMessages"])
				# @bug Not showing all of a message
				messageItem.setData(item)
				messageItem.setEditable(False)
				messageItem.setCheckable(False)
				row = (messageItem, )
				self._itemStore.appendRow(row)

	@QtCore.pyqtSlot(str)
	@misc_utils.log_exception(_moduleLogger)
	def _on_type_filter_changed(self, newItem):
		self._selectedTypeFilter = str(newItem)
		self._populate_items()

	@QtCore.pyqtSlot(str)
	@misc_utils.log_exception(_moduleLogger)
	def _on_status_filter_changed(self, newItem):
		self._selectedStatusFilter = str(newItem)
		self._populate_items()

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_messages_updated(self):
		self._populate_items()

	@QtCore.pyqtSlot(QtCore.QModelIndex)
	@misc_utils.log_exception(_moduleLogger)
	def _on_row_activated(self, index):
		rowIndex = index.row()
		item = self._itemStore.item(rowIndex, 0)
		contactDetails = item.data().toPyObject()

		name = str(contactDetails[QtCore.QString("name")])
		number = str(contactDetails[QtCore.QString("number")])
		if not name or name == number:
			name = str(contactDetails[QtCore.QString("location")])
		if not name:
			name = "Unknown"

		contactId = str(contactDetails[QtCore.QString("id")])
		title = name
		description = str(contactDetails[QtCore.QString("expandedMessages")])
		numbersWithDescriptions = [(number, "")]
		self._session.draft.add_contact(contactId, title, description, numbersWithDescriptions)


class Contacts(object):

	def __init__(self, app, session, errorLog):
		self._app = app
		self._session = session
		self._session.contactsUpdated.connect(self._on_contacts_updated)
		self._errorLog = errorLog
		self._addressBookFactories = [
			null_backend.NullAddressBookFactory(),
			file_backend.FilesystemAddressBookFactory(app.fsContactsPath),
		]
		self._addressBooks = []

		self._listSelection = QtGui.QComboBox()
		self._listSelection.addItems([])
		self._listSelection.currentIndexChanged[str].connect(self._on_filter_changed)

		self._itemStore = QtGui.QStandardItemModel()
		self._itemStore.setHorizontalHeaderLabels(["Contacts"])

		self._itemView = QtGui.QTreeView()
		self._itemView.setModel(self._itemStore)
		self._itemView.setUniformRowHeights(True)
		self._itemView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self._itemView.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
		self._itemView.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
		self._itemView.setHeaderHidden(True)
		self._itemView.activated.connect(self._on_row_activated)

		self._layout = QtGui.QVBoxLayout()
		self._layout.addWidget(self._listSelection)
		self._layout.addWidget(self._itemView)
		self._widget = QtGui.QWidget()
		self._widget.setLayout(self._layout)

		self.update_addressbooks()
		self._populate_items()

	@property
	def toplevel(self):
		return self._widget

	def enable(self):
		self._itemView.setEnabled(True)

	def disable(self):
		self._itemView.setEnabled(False)

	def clear(self):
		self._itemView.clear()

	def refresh(self, force=True):
		self._backend.update_contacts(force)

	@property
	def _backend(self):
		return self._addressBooks[self._listSelection.currentIndex()]["book"]

	def update_addressbooks(self):
		self._addressBooks = [
			{"book": book, "name": book.name}
			for factory in self._addressBookFactories
			for book in factory.get_addressbooks()
		]
		self._addressBooks.append(
			{
				"book": self._session,
				"name": "Google Voice",
			}
		)

		currentItem = str(self._listSelection.currentText())
		if currentItem == "":
			# Not loaded yet
			currentItem = "None"
		while 0 < self._listSelection.count():
			self._listSelection.removeItem(0)
		bookNames = [book["name"] for book in self._addressBooks]
		try:
			newIndex = bookNames.index(currentItem)
		except ValueError:
			# Switch over to None for the user
			newIndex = 0
			self._itemStore.clear()
			_moduleLogger.info("Addressbook %r doesn't exist anymore, switching to None" % currentItem)
		self._listSelection.addItems(bookNames)
		self._listSelection.setCurrentIndex(newIndex)

	def _populate_items(self):
		self._itemStore.clear()

		contacts = list(self._backend.get_contacts().itervalues())
		contacts.sort(key=lambda contact: contact["name"].lower())
		for item in contacts:
			name = item["name"]
			numbers = item["numbers"]
			nameItem = QtGui.QStandardItem(name)
			nameItem.setEditable(False)
			nameItem.setCheckable(False)
			nameItem.setData(item)
			row = (nameItem, )
			self._itemStore.appendRow(row)

	@QtCore.pyqtSlot(str)
	@misc_utils.log_exception(_moduleLogger)
	def _on_filter_changed(self, newItem):
		self._populate_items()

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_contacts_updated(self):
		self._populate_items()

	@QtCore.pyqtSlot(QtCore.QModelIndex)
	@misc_utils.log_exception(_moduleLogger)
	def _on_row_activated(self, index):
		rowIndex = index.row()
		item = self._itemStore.item(rowIndex, 0)
		contactDetails = item.data().toPyObject()

		name = str(contactDetails[QtCore.QString("name")])
		if not name:
			name = str(contactDetails[QtCore.QString("location")])
		if not name:
			name = "Unknown"

		contactId = str(contactDetails[QtCore.QString("contactId")])
		numbers = contactDetails[QtCore.QString("numbers")]
		numbers = [
			dict(
				(str(k), str(v))
				for (k, v) in number.iteritems()
			)
			for number in numbers
		]
		numbersWithDescriptions = [
			(
				number["phoneNumber"],
				self._choose_phonetype(number),
			)
			for number in numbers
		]
		title = name
		description = name
		self._session.draft.add_contact(contactId, title, description, numbersWithDescriptions)

	@staticmethod
	def _choose_phonetype(numberDetails):
		if "phoneTypeName" in numberDetails:
			return numberDetails["phoneTypeName"]
		elif "phoneType" in numberDetails:
			return numberDetails["phoneType"]
		else:
			return ""


class MainWindow(object):

	KEYPAD_TAB = 0
	RECENT_TAB = 1
	MESSAGES_TAB = 2
	CONTACTS_TAB = 3
	MAX_TABS = 4

	_TAB_TITLES = [
		"Dialpad",
		"History",
		"Messages",
		"Contacts",
	]
	assert len(_TAB_TITLES) == MAX_TABS

	_TAB_CLASS = [
		Dialpad,
		History,
		Messages,
		Contacts,
	]
	assert len(_TAB_CLASS) == MAX_TABS

	def __init__(self, parent, app):
		self._app = app
		self._session = session.Session(constants._data_path_)
		self._session.error.connect(self._on_session_error)
		self._session.loggedIn.connect(self._on_login)
		self._session.loggedOut.connect(self._on_logout)
		self._session.draft.recipientsChanged.connect(self._on_recipients_changed)

		self._credentialsDialog = None
		self._smsEntryDialog = None

		self._errorLog = qui_utils.QErrorLog()
		self._errorDisplay = qui_utils.ErrorDisplay(self._errorLog)

		self._tabsContents = [
			DelayedWidget(self._app)
			for i in xrange(self.MAX_TABS)
		]
		for tab in self._tabsContents:
			tab.disable()

		self._tabWidget = QtGui.QTabWidget()
		if qui_utils.screen_orientation() == QtCore.Qt.Vertical:
			self._tabWidget.setTabPosition(QtGui.QTabWidget.South)
		else:
			self._tabWidget.setTabPosition(QtGui.QTabWidget.West)
		for tabIndex, tabTitle in enumerate(self._TAB_TITLES):
			self._tabWidget.addTab(self._tabsContents[tabIndex].toplevel, tabTitle)
		self._tabWidget.currentChanged.connect(self._on_tab_changed)

		self._layout = QtGui.QVBoxLayout()
		self._layout.addWidget(self._errorDisplay.toplevel)
		self._layout.addWidget(self._tabWidget)

		centralWidget = QtGui.QWidget()
		centralWidget.setLayout(self._layout)

		self._window = QtGui.QMainWindow(parent)
		self._window.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
		qui_utils.set_autorient(self._window, True)
		qui_utils.set_stackable(self._window, True)
		self._window.setWindowTitle("%s" % constants.__pretty_app_name__)
		self._window.setCentralWidget(centralWidget)

		self._loginTabAction = QtGui.QAction(None)
		self._loginTabAction.setText("Login")
		self._loginTabAction.triggered.connect(self._on_login_requested)

		self._importTabAction = QtGui.QAction(None)
		self._importTabAction.setText("Import")
		self._importTabAction.triggered.connect(self._on_import)

		self._refreshTabAction = QtGui.QAction(None)
		self._refreshTabAction.setText("Refresh")
		self._refreshTabAction.setShortcut(QtGui.QKeySequence("CTRL+r"))
		self._refreshTabAction.triggered.connect(self._on_refresh)

		self._closeWindowAction = QtGui.QAction(None)
		self._closeWindowAction.setText("Close")
		self._closeWindowAction.setShortcut(QtGui.QKeySequence("CTRL+w"))
		self._closeWindowAction.triggered.connect(self._on_close_window)

		if IS_MAEMO:
			fileMenu = self._window.menuBar().addMenu("&File")
			fileMenu.addAction(self._loginTabAction)
			fileMenu.addAction(self._refreshTabAction)

			toolsMenu = self._window.menuBar().addMenu("&Tools")
			toolsMenu.addAction(self._importTabAction)

			self._window.addAction(self._closeWindowAction)
			self._window.addAction(self._app.quitAction)
			self._window.addAction(self._app.fullscreenAction)
		else:
			fileMenu = self._window.menuBar().addMenu("&File")
			fileMenu.addAction(self._loginTabAction)
			fileMenu.addAction(self._refreshTabAction)
			fileMenu.addAction(self._closeWindowAction)
			fileMenu.addAction(self._app.quitAction)

			viewMenu = self._window.menuBar().addMenu("&View")
			viewMenu.addAction(self._app.fullscreenAction)

			toolsMenu = self._window.menuBar().addMenu("&Tools")
			toolsMenu.addAction(self._importTabAction)

		self._window.addAction(self._app.logAction)

		self._initialize_tab(self._tabWidget.currentIndex())
		self.set_fullscreen(self._app.fullscreenAction.isChecked())
		self._window.show()

	@property
	def window(self):
		return self._window

	def walk_children(self):
		return ()

	def show(self):
		self._window.show()
		for child in self.walk_children():
			child.show()

	def hide(self):
		for child in self.walk_children():
			child.hide()
		self._window.hide()

	def close(self):
		for child in self.walk_children():
			child.window.destroyed.disconnect(self._on_child_close)
			child.close()
		self._window.close()

	def destroy(self):
		if self._session.state != self._session.LOGGEDOUT_STATE:
			self._session.logout()

	def set_fullscreen(self, isFullscreen):
		if isFullscreen:
			self._window.showFullScreen()
		else:
			self._window.showNormal()
		for child in self.walk_children():
			child.set_fullscreen(isFullscreen)

	def _initialize_tab(self, index):
		assert index < self.MAX_TABS
		if not self._tabsContents[index].has_child():
			tab = self._TAB_CLASS[index](self._app, self._session, self._errorLog)
			self._tabsContents[index].set_child(tab)
			self._tabsContents[index].refresh(force=False)

	@QtCore.pyqtSlot(str)
	@misc_utils.log_exception(_moduleLogger)
	def _on_session_error(self, message):
		self._errorLog.push_message(message)

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_login(self):
		for tab in self._tabsContents:
			tab.enable()

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_logout(self):
		for tab in self._tabsContents:
			tab.disable()

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_recipients_changed(self):
		if self._session.draft.get_num_contacts() == 0:
			return

		if self._smsEntryDialog is None:
			self._smsEntryDialog = SMSEntryWindow(self.window, self._app, self._session, self._errorLog)
		pass

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_login_requested(self, checked = True):
		if self._credentialsDialog is None:
			self._credentialsDialog = CredentialsDialog()
		username, password = self._credentialsDialog.run("", "", self.window)
		self._session.login(username, password)

	@QtCore.pyqtSlot(int)
	@misc_utils.log_exception(_moduleLogger)
	def _on_tab_changed(self, index):
		self._initialize_tab(index)

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_refresh(self, checked = True):
		index = self._tabWidget.currentIndex()
		self._tabsContents[index].refresh(force=True)

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_import(self, checked = True):
		csvName = QtGui.QFileDialog.getOpenFileName(self._window, caption="Import", filter="CSV Files (*.csv)")
		if not csvName:
			return
		shutil.copy2(csvName, self._app.fsContactsPath)
		self._tabsContents[self.CONTACTS_TAB].update_addressbooks()

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_close_window(self, checked = True):
		self.close()


def make_ugly(prettynumber):
	"""
	function to take a phone number and strip out all non-numeric
	characters

	>>> make_ugly("+012-(345)-678-90")
	'+01234567890'
	"""
	return normalize_number(prettynumber)


def normalize_number(prettynumber):
	"""
	function to take a phone number and strip out all non-numeric
	characters

	>>> normalize_number("+012-(345)-678-90")
	'+01234567890'
	>>> normalize_number("1-(345)-678-9000")
	'+13456789000'
	>>> normalize_number("+1-(345)-678-9000")
	'+13456789000'
	"""
	uglynumber = re.sub('[^0-9+]', '', prettynumber)

	if uglynumber.startswith("+"):
		pass
	elif uglynumber.startswith("1"):
		uglynumber = "+"+uglynumber
	elif 10 <= len(uglynumber):
		assert uglynumber[0] not in ("+", "1")
		uglynumber = "+1"+uglynumber
	else:
		pass

	return uglynumber


def _make_pretty_with_areacode(phonenumber):
	prettynumber = "(%s)" % (phonenumber[0:3], )
	if 3 < len(phonenumber):
		prettynumber += " %s" % (phonenumber[3:6], )
		if 6 < len(phonenumber):
			prettynumber += "-%s" % (phonenumber[6:], )
	return prettynumber


def _make_pretty_local(phonenumber):
	prettynumber = "%s" % (phonenumber[0:3], )
	if 3 < len(phonenumber):
		prettynumber += "-%s" % (phonenumber[3:], )
	return prettynumber


def _make_pretty_international(phonenumber):
	prettynumber = phonenumber
	if phonenumber.startswith("1"):
		prettynumber = "1 "
		prettynumber += _make_pretty_with_areacode(phonenumber[1:])
	return prettynumber


def make_pretty(phonenumber):
	"""
	Function to take a phone number and return the pretty version
	pretty numbers:
		if phonenumber begins with 0:
			...-(...)-...-....
		if phonenumber begins with 1: ( for gizmo callback numbers )
			1 (...)-...-....
		if phonenumber is 13 digits:
			(...)-...-....
		if phonenumber is 10 digits:
			...-....
	>>> make_pretty("12")
	'12'
	>>> make_pretty("1234567")
	'123-4567'
	>>> make_pretty("2345678901")
	'+1 (234) 567-8901'
	>>> make_pretty("12345678901")
	'+1 (234) 567-8901'
	>>> make_pretty("01234567890")
	'+012 (345) 678-90'
	>>> make_pretty("+01234567890")
	'+012 (345) 678-90'
	>>> make_pretty("+12")
	'+1 (2)'
	>>> make_pretty("+123")
	'+1 (23)'
	>>> make_pretty("+1234")
	'+1 (234)'
	"""
	if phonenumber is None or phonenumber is "":
		return ""

	phonenumber = normalize_number(phonenumber)

	if phonenumber[0] == "+":
		prettynumber = _make_pretty_international(phonenumber[1:])
		if not prettynumber.startswith("+"):
			prettynumber = "+"+prettynumber
	elif 8 < len(phonenumber) and phonenumber[0] in ("1", ):
		prettynumber = _make_pretty_international(phonenumber)
	elif 7 < len(phonenumber):
		prettynumber = _make_pretty_with_areacode(phonenumber)
	elif 3 < len(phonenumber):
		prettynumber = _make_pretty_local(phonenumber)
	else:
		prettynumber = phonenumber
	return prettynumber.strip()


def abbrev_relative_date(date):
	"""
	>>> abbrev_relative_date("42 hours ago")
	'42 h'
	>>> abbrev_relative_date("2 days ago")
	'2 d'
	>>> abbrev_relative_date("4 weeks ago")
	'4 w'
	"""
	parts = date.split(" ")
	return "%s %s" % (parts[0], parts[1][0])


def run():
	app = QtGui.QApplication([])
	handle = Dialcentral(app)
	qtpie.init_pies()
	return app.exec_()


if __name__ == "__main__":
	logFormat = '(%(relativeCreated)5d) %(levelname)-5s %(threadName)s.%(name)s.%(funcName)s: %(message)s'
	logging.basicConfig(level=logging.DEBUG, format=logFormat)
	try:
		os.makedirs(constants._data_path_)
	except OSError, e:
		if e.errno != 17:
			raise

	val = run()
	sys.exit(val)
