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

	def __init__(self, app):
		self._app = app
		self._widget = QtGui.QWidget()

	@property
	def toplevel(self):
		return self._widget

	def enable(self):
		pass

	def disable(self):
		pass

	def refresh(self):
		pass


class Messages(object):

	def __init__(self, app):
		self._app = app
		self._widget = QtGui.QWidget()

	@property
	def toplevel(self):
		return self._widget

	def enable(self):
		pass

	def disable(self):
		pass

	def refresh(self):
		pass


class Contacts(object):

	def __init__(self, app):
		self._app = app
		self._widget = QtGui.QWidget()

	@property
	def toplevel(self):
		return self._widget

	def enable(self):
		pass

	def disable(self):
		pass

	def refresh(self):
		pass


class MainWindow(object):

	KEYPAD_TAB = 0
	RECENT_TAB = 1
	MESSAGES_TAB = 2
	CONTACTS_TAB = 3
	ACCOUNT_TAB = 4

	def __init__(self, parent, app):
		self._fsContactsPath = os.path.join(constants._data_path_, "contacts")
		self._app = app

		self._errorDisplay = QErrorDisplay()

		self._dialpad = Dialpad(self._app)
		self._history = History(self._app)
		self._messages = Messages(self._app)
		self._contacts = Contacts(self._app)

		self._tabs = QtGui.QTabWidget()
		if maeqt.screen_orientation() == QtCore.Qt.Vertical:
			self._tabs.setTabPosition(QtGui.QTabWidget.South)
		else:
			self._tabs.setTabPosition(QtGui.QTabWidget.West)
		self._tabs.addTab(self._dialpad.toplevel, "Dialpad")
		self._tabs.addTab(self._history.toplevel, "History")
		self._tabs.addTab(self._messages.toplevel, "Messages")
		self._tabs.addTab(self._contacts.toplevel, "Contacts")

		self._layout = QtGui.QVBoxLayout()
		self._layout.addWidget(self._errorDisplay.toplevel)
		self._layout.addWidget(self._tabs)

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

	def _populate_tab(self, index):
		pass

	@misc_utils.log_exception(_moduleLogger)
	def _on_login(self, checked = True):
		pass

	@misc_utils.log_exception(_moduleLogger)
	def _on_tab_changed(self, index):
		self._populate_tab(index)

	@misc_utils.log_exception(_moduleLogger)
	def _on_refresh(self, checked = True):
		index = self._tabs.currentIndex()
		self._populate_tab(index)

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
