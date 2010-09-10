#!/usr/bin/env python
# -*- coding: UTF8 -*-

from __future__ import with_statement

import sys
import os
import shutil
import simplejson
import logging

from PyQt4 import QtGui
from PyQt4 import QtCore

import constants
import maeqt
from util import qtpie
from util import misc as misc_utils


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

	@misc_utils.log_exception(_moduleLogger)
	def _on_app_quit(self, checked = False):
		self.save_settings()

	@misc_utils.log_exception(_moduleLogger)
	def _on_child_close(self, obj = None):
		self._mainWindow = None

	@misc_utils.log_exception(_moduleLogger)
	def _on_toggle_fullscreen(self, checked = False):
		for window in self._walk_children():
			window.set_fullscreen(checked)

	@misc_utils.log_exception(_moduleLogger)
	def _on_log(self, checked = False):
		with open(constants._user_logpath_, "r") as f:
			logLines = f.xreadlines()
			log = "".join(logLines)
			self._clipboard.setText(log)

	@misc_utils.log_exception(_moduleLogger)
	def _on_quit(self, checked = False):
		self._close_windows()


class QErrorDisplay(object):

	def __init__(self):
		self._messages = []

		errorIcon = maeqt.get_theme_icon(("dialog-error", "app_install_error", "gtk-dialog-error"))
		self._severityIcon = errorIcon.pixmap(32, 32)
		self._severityLabel = QtGui.QLabel()
		self._severityLabel.setPixmap(self._severityIcon)

		self._message = QtGui.QLabel()
		self._message.setText("Boo")

		closeIcon = maeqt.get_theme_icon(("window-close", "general_close", "gtk-close"))
		self._closeLabel = QtGui.QPushButton(closeIcon, "")
		self._closeLabel.clicked.connect(self._on_close)

		self._controlLayout = QtGui.QHBoxLayout()
		self._controlLayout.addWidget(self._severityLabel)
		self._controlLayout.addWidget(self._message)
		self._controlLayout.addWidget(self._closeLabel)

		self._topLevelLayout = QtGui.QHBoxLayout()
		self._topLevelLayout.addLayout(self._controlLayout)
		self._widget = QtGui.QWidget()
		self._widget.setLayout(self._topLevelLayout)
		self._hide_message()

	@property
	def toplevel(self):
		return self._widget

	def push_message(self, message):
		self._messages.append(message)
		if 1 == len(self._messages):
			self._show_message(message)

	def push_exception(self):
		userMessage = str(sys.exc_info()[1])
		_moduleLogger.exception(userMessage)
		self.push_message(userMessage)

	def pop_message(self):
		del self._messages[0]
		if 0 == len(self._messages):
			self._hide_message()
		else:
			self._message.setText(self._messages[0])

	def _on_close(self, *args):
		self.pop_message()

	def _show_message(self, message):
		self._message.setText(message)
		self._widget.show()

	def _hide_message(self):
		self._message.setText("")
		self._widget.hide()


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
		self._layout.addLayout(self._buttonLayout)

		centralWidget = QtGui.QWidget()
		centralWidget.setLayout(self._layout)

		self._dialog = QtGui.QDialog()
		self._dialog.setWindowTitle("Login")
		self._dialog.setCentralWidget(centralWidget)
		maeqt.set_autorient(self._dialog, True)
		self._buttonLayout.accepted.connect(self._dialog.accept)
		self._buttonLayout.rejected.connect(self._dialog.reject)

	def run(self, defaultUsername, defaultPassword, parent=None):
		self._dialog.setParent(parent)
		self._usernameField.setText(defaultUsername)
		self._passwordField.setText(defaultPassword)

		response = self._dialog.exec_()
		if response == QtGui.QDialog.Accepted:
			return str(self._usernameField.text()), str(self._passwordField.text())
		elif response == QtGui.QDialog.Rejected:
			raise RuntimeError("Login Cancelled")


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

		centralWidget = QtGui.QWidget()
		centralWidget.setLayout(self._layout)

		self._dialog = QtGui.QDialog()
		self._dialog.setWindowTitle("Login")
		self._dialog.setCentralWidget(centralWidget)
		maeqt.set_autorient(self._dialog, True)
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

	def _on_clear(self, checked = False):
		self._doClear = True
		self._dialog.accept()


class SMSEntryWindow(object):

	def __init__(self, parent, app):
		self._contacts = []
		self._app = app

		self._history = QtGui.QListView()
		self._smsEntry = QtGui.QTextEdit()
		self._smsEntry.textChanged.connect(self._on_letter_count_changed)

		self._entryLayout = QtGui.QVBoxLayout()
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
		self._numberSelector = None
		self._smsButton = QtGui.QPushButton("SMS")
		self._dialButton = QtGui.QPushButton("Dial")

		self._buttonLayout = QtGui.QHBoxLayout()
		self._buttonLayout.addWidget(self._characterCountLabel)
		self._buttonLayout.addWidget(self._smsButton)
		self._buttonLayout.addWidget(self._dialButton)

		self._layout = QtGui.QVBoxLayout()
		self._layout.addLayout(self._entryLayout)
		self._layout.addLayout(self._buttonLayout)

		centralWidget = QtGui.QWidget()
		centralWidget.setLayout(self._layout)

		self._window = QtGui.QMainWindow(parent)
		self._window.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
		maeqt.set_autorient(self._window, True)
		maeqt.set_stackable(self._window, True)
		self._window.setWindowTitle("Contact")
		self._window.setCentralWidget(centralWidget)

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

	def refresh(self):
		if self._child is not None:
			self._child.refresh()


class Dialpad(object):

	def __init__(self, app):
		self._app = app

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

	def refresh(self):
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

	@misc_utils.log_exception(_moduleLogger)
	def _on_sms_clicked(self, checked = False):
		number = str(self._entry.text())
		self._entry.clear()
		print "sms", number

	@misc_utils.log_exception(_moduleLogger)
	def _on_call_clicked(self, checked = False):
		number = str(self._entry.text())
		self._entry.clear()
		print "call", number


class History(object):

	DATE_IDX = 0
	ACTION_IDX = 1
	NUMBER_IDX = 2
	FROM_IDX = 3
	MAX_IDX = 4

	HISTORY_ITEM_TYPES = ["All", "Received", "Missed", "Placed"]
	HISTORY_COLUMNS = ["When", "What", "Number", "From"]
	assert len(HISTORY_COLUMNS) == MAX_IDX

	def __init__(self, app):
		self._selectedFilter = self.HISTORY_ITEM_TYPES[0]
		self._app = app

		self._typeSelection = QtGui.QComboBox()
		self._typeSelection.addItems(self.HISTORY_ITEM_TYPES)
		self._typeSelection.setCurrentIndex(
			self.HISTORY_ITEM_TYPES.index(self._selectedFilter)
		)
		self._typeSelection.currentIndexChanged.connect(self._on_filter_changed)

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

	@property
	def toplevel(self):
		return self._widget

	def enable(self):
		self._itemView.setEnabled(True)

	def disable(self):
		self._itemView.setEnabled(False)

	def clear(self):
		self._itemView.clear()

	def refresh(self):
		pass

	@misc_utils.log_exception(_moduleLogger)
	def _on_filter_changed(self, newItem):
		self._selectedFilter = str(newItem)

	@misc_utils.log_exception(_moduleLogger)
	def _on_row_activated(self, index):
		rowIndex = index.row()


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

	def __init__(self, app):
		self._selectedTypeFilter = self.ALL_TYPES
		self._selectedStatusFilter = self.ALL_STATUS
		self._app = app

		self._typeSelection = QtGui.QComboBox()
		self._typeSelection.addItems(self.MESSAGE_TYPES)
		self._typeSelection.setCurrentIndex(
			self.MESSAGE_TYPES.index(self._selectedTypeFilter)
		)
		self._typeSelection.currentIndexChanged.connect(self._on_type_filter_changed)

		self._statusSelection = QtGui.QComboBox()
		self._statusSelection.addItems(self.MESSAGE_STATUSES)
		self._statusSelection.setCurrentIndex(
			self.MESSAGE_STATUSES.index(self._selectedStatusFilter)
		)
		self._statusSelection.currentIndexChanged.connect(self._on_status_filter_changed)

		self._selectionLayout = QtGui.QHBoxLayout()
		self._selectionLayout.addWidget(self._typeSelection)
		self._selectionLayout.addWidget(self._statusSelection)

		self._itemStore = QtGui.QStandardItemModel()
		self._itemStore.setHorizontalHeaderLabels(["Messages"])

		self._itemView = QtGui.QTreeView()
		self._itemView.setModel(self._itemStore)
		self._itemView.setUniformRowHeights(True)
		self._itemView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self._itemView.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
		self._itemView.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
		self._itemView.setHeaderHidden(True)
		self._itemView.activated.connect(self._on_row_activated)

		self._layout = QtGui.QVBoxLayout()
		self._layout.addLayout(self._selectionLayout)
		self._layout.addWidget(self._itemView)
		self._widget = QtGui.QWidget()
		self._widget.setLayout(self._layout)

	@property
	def toplevel(self):
		return self._widget

	def enable(self):
		self._itemView.setEnabled(True)

	def disable(self):
		self._itemView.setEnabled(False)

	def clear(self):
		self._itemView.clear()

	def refresh(self):
		pass

	@misc_utils.log_exception(_moduleLogger)
	def _on_type_filter_changed(self, newItem):
		self._selectedTypeFilter = str(newItem)

	@misc_utils.log_exception(_moduleLogger)
	def _on_status_filter_changed(self, newItem):
		self._selectedStatusFilter = str(newItem)

	@misc_utils.log_exception(_moduleLogger)
	def _on_row_activated(self, index):
		rowIndex = index.row()


class Contacts(object):

	def __init__(self, app):
		self._selectedFilter = ""
		self._app = app

		self._listSelection = QtGui.QComboBox()
		self._listSelection.addItems([])
		#self._listSelection.setCurrentIndex(self.HISTORY_ITEM_TYPES.index(self._selectedFilter))
		self._listSelection.currentIndexChanged.connect(self._on_filter_changed)

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

	@property
	def toplevel(self):
		return self._widget

	def enable(self):
		self._itemView.setEnabled(True)

	def disable(self):
		self._itemView.setEnabled(False)

	def clear(self):
		self._itemView.clear()

	def refresh(self):
		pass

	@misc_utils.log_exception(_moduleLogger)
	def _on_filter_changed(self, newItem):
		self._selectedFilter = str(newItem)

	@misc_utils.log_exception(_moduleLogger)
	def _on_row_activated(self, index):
		rowIndex = index.row()


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
		self._fsContactsPath = os.path.join(constants._data_path_, "contacts")
		self._app = app

		self._errorDisplay = QErrorDisplay()

		self._tabsContents = [
			DelayedWidget(self._app)
			for i in xrange(self.MAX_TABS)
		]

		self._tabWidget = QtGui.QTabWidget()
		if maeqt.screen_orientation() == QtCore.Qt.Vertical:
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
		maeqt.set_autorient(self._window, True)
		maeqt.set_stackable(self._window, True)
		self._window.setWindowTitle("%s" % constants.__pretty_app_name__)
		self._window.setCentralWidget(centralWidget)

		self._loginTabAction = QtGui.QAction(None)
		self._loginTabAction.setText("Login")
		self._loginTabAction.triggered.connect(self._on_login)

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
			self._tabsContents[index].set_child(self._TAB_CLASS[index](self._app))

	@misc_utils.log_exception(_moduleLogger)
	def _on_login(self, checked = True):
		pass

	@misc_utils.log_exception(_moduleLogger)
	def _on_tab_changed(self, index):
		self._initialize_tab(index)

	@misc_utils.log_exception(_moduleLogger)
	def _on_refresh(self, checked = True):
		index = self._tabWidget.currentIndex()
		self._tabsContents[index].refresh()

	@misc_utils.log_exception(_moduleLogger)
	def _on_import(self, checked = True):
		csvName = QtGui.QFileDialog.getOpenFileName(self._window, caption="Import", filter="CSV Files (*.csv)")
		if not csvName:
			return
		shutil.copy2(csvName, self._fsContactsPath)

	@misc_utils.log_exception(_moduleLogger)
	def _on_close_window(self, checked = True):
		self.close()


def run():
	app = QtGui.QApplication([])
	handle = Dialcentral(app)
	qtpie.init_pies()
	return app.exec_()


if __name__ == "__main__":
	logging.basicConfig(level = logging.DEBUG)
	try:
		os.makedirs(constants._data_path_)
	except OSError, e:
		if e.errno != 17:
			raise

	val = run()
	sys.exit(val)
