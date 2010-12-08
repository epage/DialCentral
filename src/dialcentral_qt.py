#!/usr/bin/env python
# -*- coding: UTF8 -*-

from __future__ import with_statement

import os
import base64
import ConfigParser
import functools
import logging

from PyQt4 import QtGui
from PyQt4 import QtCore

import constants
from util import qtpie
from util import qui_utils
from util import misc as misc_utils

import session


_moduleLogger = logging.getLogger(__name__)
IS_MAEMO = True


class Dialcentral(object):

	_DATA_PATHS = [
		os.path.join(os.path.dirname(__file__), "../share"),
		os.path.join(os.path.dirname(__file__), "../data"),
	]

	def __init__(self, app):
		self._app = app
		self._recent = []
		self._hiddenCategories = set()
		self._hiddenUnits = {}
		self._clipboard = QtGui.QApplication.clipboard()
		self._dataPath = None

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
		self._mainWindow = MainWindow(None, self)
		self._mainWindow.window.destroyed.connect(self._on_child_close)

		self.load_settings()

		self._mainWindow.show()
		self._idleDelay = QtCore.QTimer()
		self._idleDelay.setSingleShot(True)
		self._idleDelay.setInterval(0)
		self._idleDelay.timeout.connect(lambda: self._mainWindow.start())
		self._idleDelay.start()

	def load_settings(self):
		try:
			config = ConfigParser.SafeConfigParser()
			config.read(constants._user_settings_)
		except IOError, e:
			_moduleLogger.info("No settings")
			return
		except ValueError:
			_moduleLogger.info("Settings were corrupt")
			return
		except ConfigParser.MissingSectionHeaderError:
			_moduleLogger.info("Settings were corrupt")
			return
		except Exception:
			_moduleLogger.exception("Unknown loading error")

		blobs = "", ""
		isFullscreen = False
		tabIndex = 0
		try:
			blobs = (
				config.get(constants.__pretty_app_name__, "bin_blob_%i" % i)
				for i in xrange(len(self._mainWindow.get_default_credentials()))
			)
			isFullscreen = config.getboolean(constants.__pretty_app_name__, "fullscreen")
			tabIndex = config.getint(constants.__pretty_app_name__, "tab")
		except ConfigParser.NoOptionError, e:
			_moduleLogger.info(
				"Settings file %s is missing option %s" % (
					constants._user_settings_,
					e.option,
				),
			)
		except ConfigParser.NoSectionError, e:
			_moduleLogger.info(
				"Settings file %s is missing section %s" % (
					constants._user_settings_,
					e.section,
				),
			)
			return
		except Exception:
			_moduleLogger.exception("Unknown loading error")
			return

		creds = (
			base64.b64decode(blob)
			for blob in blobs
		)
		self._mainWindow.set_default_credentials(*creds)
		self._fullscreenAction.setChecked(isFullscreen)
		self._mainWindow.set_current_tab(tabIndex)
		self._mainWindow.load_settings(config)

	def save_settings(self):
		_moduleLogger.info("Saving settings")
		config = ConfigParser.SafeConfigParser()

		config.add_section(constants.__pretty_app_name__)
		config.set(constants.__pretty_app_name__, "tab", str(self._mainWindow.get_current_tab()))
		config.set(constants.__pretty_app_name__, "fullscreen", str(self._fullscreenAction.isChecked()))
		for i, value in enumerate(self._mainWindow.get_default_credentials()):
			blob = base64.b64encode(value)
			config.set(constants.__pretty_app_name__, "bin_blob_%i" % i, blob)

		self._mainWindow.save_settings(config)

		with open(constants._user_settings_, "wb") as configFile:
			config.write(configFile)

	def get_icon(self, name):
		if self._dataPath is None:
			for path in self._DATA_PATHS:
				if os.path.exists(os.path.join(path, name)):
					self._dataPath = path
					break
		if self._dataPath is not None:
			icon = QtGui.QIcon(os.path.join(self._dataPath, name))
			return icon
		else:
			return None

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
			self.save_settings()
			self._mainWindow.window.destroyed.disconnect(self._on_child_close)
			self._mainWindow.close()
			self._mainWindow = None

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_app_quit(self, checked = False):
		if self._mainWindow is not None:
			self.save_settings()
			self._mainWindow.destroy()

	@QtCore.pyqtSlot(QtCore.QObject)
	@misc_utils.log_exception(_moduleLogger)
	def _on_child_close(self, obj = None):
		if self._mainWindow is not None:
			self.save_settings()
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


class DelayedWidget(object):

	def __init__(self, app, settingsNames):
		self._layout = QtGui.QVBoxLayout()
		self._layout.setContentsMargins(0, 0, 0, 0)
		self._widget = QtGui.QWidget()
		self._widget.setContentsMargins(0, 0, 0, 0)
		self._widget.setLayout(self._layout)
		self._settings = dict((name, "") for name in settingsNames)

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

		self._child.set_settings(self._settings)

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

	def get_settings(self):
		if self._child is not None:
			return self._child.get_settings()
		else:
			return self._settings

	def set_settings(self, settings):
		if self._child is not None:
			self._child.set_settings(settings)
		else:
			self._settings = settings


def _tab_factory(tab, app, session, errorLog):
	import gv_views
	return gv_views.__dict__[tab](app, session, errorLog)


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

	_TAB_ICONS = [
		"dialpad.png",
		"history.png",
		"messages.png",
		"contacts.png",
	]
	assert len(_TAB_ICONS) == MAX_TABS

	_TAB_CLASS = [
		functools.partial(_tab_factory, "Dialpad"),
		functools.partial(_tab_factory, "History"),
		functools.partial(_tab_factory, "Messages"),
		functools.partial(_tab_factory, "Contacts"),
	]
	assert len(_TAB_CLASS) == MAX_TABS

	# Hack to allow delay importing/loading of tabs
	_TAB_SETTINGS_NAMES = [
		(),
		("filter", ),
		("status", "type"),
		("selectedAddressbook", ),
	]
	assert len(_TAB_SETTINGS_NAMES) == MAX_TABS

	def __init__(self, parent, app):
		self._app = app
		self._session = session.Session(constants._data_path_)
		self._session.error.connect(self._on_session_error)
		self._session.loggedIn.connect(self._on_login)
		self._session.loggedOut.connect(self._on_logout)
		self._session.draft.recipientsChanged.connect(self._on_recipients_changed)
		self._defaultCredentials = "", ""
		self._curentCredentials = "", ""
		self._currentTab = 0

		self._credentialsDialog = None
		self._smsEntryDialog = None
		self._accountDialog = None
		self._aboutDialog = None

		self._errorLog = qui_utils.QErrorLog()
		self._errorDisplay = qui_utils.ErrorDisplay(self._errorLog)

		self._tabsContents = [
			DelayedWidget(self._app, self._TAB_SETTINGS_NAMES[i])
			for i in xrange(self.MAX_TABS)
		]
		for tab in self._tabsContents:
			tab.disable()

		self._tabWidget = QtGui.QTabWidget()
		if qui_utils.screen_orientation() == QtCore.Qt.Vertical:
			self._tabWidget.setTabPosition(QtGui.QTabWidget.South)
		else:
			self._tabWidget.setTabPosition(QtGui.QTabWidget.West)
		for tabIndex, (tabTitle, tabIcon) in enumerate(
			zip(self._TAB_TITLES, self._TAB_ICONS)
		):
			if IS_MAEMO:
				icon = self._app.get_icon(tabIcon)
				if icon is None:
					self._tabWidget.addTab(self._tabsContents[tabIndex].toplevel, tabTitle)
				else:
					self._tabWidget.addTab(self._tabsContents[tabIndex].toplevel, icon, "")
			else:
				icon = self._app.get_icon(tabIcon)
				self._tabWidget.addTab(self._tabsContents[tabIndex].toplevel, icon, tabTitle)
		self._tabWidget.currentChanged.connect(self._on_tab_changed)
		self._tabWidget.setContentsMargins(0, 0, 0, 0)

		self._layout = QtGui.QVBoxLayout()
		self._layout.setContentsMargins(0, 0, 0, 0)
		self._layout.addWidget(self._errorDisplay.toplevel)
		self._layout.addWidget(self._tabWidget)

		centralWidget = QtGui.QWidget()
		centralWidget.setLayout(self._layout)
		centralWidget.setContentsMargins(0, 0, 0, 0)

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

		self._accountTabAction = QtGui.QAction(None)
		self._accountTabAction.setText("Account")
		self._accountTabAction.triggered.connect(self._on_account)

		self._refreshTabAction = QtGui.QAction(None)
		self._refreshTabAction.setText("Refresh")
		self._refreshTabAction.setShortcut(QtGui.QKeySequence("CTRL+r"))
		self._refreshTabAction.triggered.connect(self._on_refresh)

		self._aboutAction = QtGui.QAction(None)
		self._aboutAction.setText("About")
		self._aboutAction.triggered.connect(self._on_about)

		self._closeWindowAction = QtGui.QAction(None)
		self._closeWindowAction.setText("Close")
		self._closeWindowAction.setShortcut(QtGui.QKeySequence("CTRL+w"))
		self._closeWindowAction.triggered.connect(self._on_close_window)

		if IS_MAEMO:
			fileMenu = self._window.menuBar().addMenu("&File")
			fileMenu.addAction(self._loginTabAction)
			fileMenu.addAction(self._refreshTabAction)

			toolsMenu = self._window.menuBar().addMenu("&Tools")
			toolsMenu.addAction(self._accountTabAction)
			toolsMenu.addAction(self._importTabAction)
			toolsMenu.addAction(self._aboutAction)

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
			toolsMenu.addAction(self._accountTabAction)
			toolsMenu.addAction(self._importTabAction)
			toolsMenu.addAction(self._aboutAction)

		self._window.addAction(self._app.logAction)

		self._initialize_tab(self._tabWidget.currentIndex())
		self.set_fullscreen(self._app.fullscreenAction.isChecked())

	@property
	def window(self):
		return self._window

	def set_default_credentials(self, username, password):
		self._defaultCredentials = username, password

	def get_default_credentials(self):
		return self._defaultCredentials

	def walk_children(self):
		return (diag for diag in (
			self._credentialsDialog,
			self._smsEntryDialog,
			self._accountDialog,
			self._aboutDialog,
			)
			if diag is not None
		)

	def start(self):
		assert self._session.state == self._session.LOGGEDOUT_STATE
		if self._defaultCredentials != ("", ""):
			username, password = self._defaultCredentials[0], self._defaultCredentials[1]
			self._curentCredentials = username, password
			self._session.login(username, password)
		else:
			self._prompt_for_login()

	def close(self):
		for child in self.walk_children():
			child.close()
		self._window.close()

	def destroy(self):
		if self._session.state != self._session.LOGGEDOUT_STATE:
			self._session.logout()

	def get_current_tab(self):
		return self._currentTab

	def set_current_tab(self, tabIndex):
		self._tabWidget.setCurrentIndex(tabIndex)

	def load_settings(self, config):
		backendId = 2 # For backwards compatibility
		for tabIndex, tabTitle in enumerate(self._TAB_TITLES):
			sectionName = "%s - %s" % (backendId, tabTitle)
			settings = self._tabsContents[tabIndex].get_settings()
			for settingName in settings.iterkeys():
				try:
					settingValue = config.get(sectionName, settingName)
				except ConfigParser.NoOptionError, e:
					_moduleLogger.info(
						"Settings file %s is missing section %s" % (
							constants._user_settings_,
							e.section,
						),
					)
					return
				except ConfigParser.NoSectionError, e:
					_moduleLogger.info(
						"Settings file %s is missing section %s" % (
							constants._user_settings_,
							e.section,
						),
					)
					return
				except Exception:
					_moduleLogger.exception("Unknown loading error")
					return
				settings[settingName] = settingValue
			self._tabsContents[tabIndex].set_settings(settings)

	def save_settings(self, config):
		backendId = 2 # For backwards compatibility
		for tabIndex, tabTitle in enumerate(self._TAB_TITLES):
			sectionName = "%s - %s" % (backendId, tabTitle)
			config.add_section(sectionName)
			tabSettings = self._tabsContents[tabIndex].get_settings()
			for settingName, settingValue in tabSettings.iteritems():
				config.set(sectionName, settingName, settingValue)

	def show(self):
		self._window.show()
		for child in self.walk_children():
			child.show()

	def hide(self):
		for child in self.walk_children():
			child.hide()
		self._window.hide()

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

	def _prompt_for_login(self):
		if self._credentialsDialog is None:
			import dialogs
			self._credentialsDialog = dialogs.CredentialsDialog(self._app)
		username, password = self._credentialsDialog.run(
			self._defaultCredentials[0], self._defaultCredentials[1], self.window
		)
		self._curentCredentials = username, password
		self._session.login(username, password)

	def _show_account_dialog(self):
		if self._accountDialog is None:
			import dialogs
			self._accountDialog = dialogs.AccountDialog(self._app)
		self._accountDialog.set_callbacks(
			self._session.get_callback_numbers(), self._session.get_callback_number()
		)
		self._accountDialog.accountNumber = self._session.get_account_number()
		response = self._accountDialog.run()
		if response == QtGui.QDialog.Accepted:
			if self._accountDialog.doClear:
				self._session.logout_and_clear()
			else:
				callbackNumber = self._accountDialog.selectedCallback
				self._session.set_callback_number(callbackNumber)
		elif response == QtGui.QDialog.Rejected:
			_moduleLogger.info("Cancelled")
		else:
			_moduleLogger.info("Unknown response")

	@QtCore.pyqtSlot(str)
	@misc_utils.log_exception(_moduleLogger)
	def _on_session_error(self, message):
		self._errorLog.push_message(message)

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_login(self):
		if self._defaultCredentials != self._curentCredentials:
			self._show_account_dialog()
		self._defaultCredentials = self._curentCredentials
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
			import dialogs
			self._smsEntryDialog = dialogs.SMSEntryWindow(self.window, self._app, self._session, self._errorLog)
		pass

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_login_requested(self, checked = True):
		self._prompt_for_login()

	@QtCore.pyqtSlot(int)
	@misc_utils.log_exception(_moduleLogger)
	def _on_tab_changed(self, index):
		self._currentTab = index
		self._initialize_tab(index)

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_refresh(self, checked = True):
		self._tabsContents[self._currentTab].refresh(force=True)

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_import(self, checked = True):
		csvName = QtGui.QFileDialog.getOpenFileName(self._window, caption="Import", filter="CSV Files (*.csv)")
		if not csvName:
			return
		import shutil
		shutil.copy2(csvName, self._app.fsContactsPath)
		self._tabsContents[self.CONTACTS_TAB].update_addressbooks()

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_account(self, checked = True):
		self._show_account_dialog()

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	def _on_about(self, checked = True):
		if self._aboutDialog is None:
			import dialogs
			self._aboutDialog = dialogs.AboutDialog(self._app)
		response = self._aboutDialog.run()

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_close_window(self, checked = True):
		self.close()


def run():
	app = QtGui.QApplication([])
	handle = Dialcentral(app)
	qtpie.init_pies()
	return app.exec_()


if __name__ == "__main__":
	import sys

	logFormat = '(%(relativeCreated)5d) %(levelname)-5s %(threadName)s.%(name)s.%(funcName)s: %(message)s'
	logging.basicConfig(level=logging.DEBUG, format=logFormat)
	try:
		os.makedirs(constants._data_path_)
	except OSError, e:
		if e.errno != 17:
			raise

	val = run()
	sys.exit(val)
