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

		self._tabs = QtGui.QTabWidget()
		if maeqt.screen_orientation() == QtCore.Qt.Vertical:
			self._tabs.setTabPosition(QtGui.QTabWidget.South)
		else:
			self._tabs.setTabPosition(QtGui.QTabWidget.West)

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
