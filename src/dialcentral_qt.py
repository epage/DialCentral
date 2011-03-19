#!/usr/bin/env python
# -*- coding: UTF8 -*-

from __future__ import with_statement

import os
import base64
import ConfigParser
import functools
import logging
import logging.handlers

from PyQt4 import QtGui
from PyQt4 import QtCore

import constants
import alarm_handler
from util import qtpie
from util import qwrappers
from util import qui_utils
from util import misc as misc_utils

import session


_moduleLogger = logging.getLogger(__name__)


class Dialcentral(qwrappers.ApplicationWrapper):

	_DATA_PATHS = [
		os.path.join(os.path.dirname(__file__), "../share"),
		os.path.join(os.path.dirname(__file__), "../data"),
	]

	def __init__(self, app):
		self._dataPath = None
		self._aboutDialog = None
		self.notifyOnMissed = False
		self.notifyOnVoicemail = False
		self.notifyOnSms = False

		self._streamHandler = None
		self._ledHandler = None
		self._alarmHandler = alarm_handler.AlarmHandler()

		qwrappers.ApplicationWrapper.__init__(self, app, constants)

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

		self._mainWindow.load_settings(config)

	def save_settings(self):
		_moduleLogger.info("Saving settings")
		config = ConfigParser.SafeConfigParser()

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

	def get_resource(self, name):
		if self._dataPath is None:
			for path in self._DATA_PATHS:
				if os.path.exists(os.path.join(path, name)):
					self._dataPath = path
					break
		if self._dataPath is not None:
			return os.path.join(self._dataPath, name)
		else:
			return None

	def _close_windows(self):
		qwrappers.ApplicationWrapper._close_windows(self)
		if self._aboutDialog  is not None:
			self._aboutDialog.close()

	@property
	def fsContactsPath(self):
		return os.path.join(constants._data_path_, "contacts")

	@property
	def streamHandler(self):
		if self._streamHandler is None:
			import stream_handler
			self._streamHandler = stream_handler.StreamHandler()
		return self._streamHandler

	@property
	def alarmHandler(self):
		return self._alarmHandler

	@property
	def ledHandler(self):
		if self._ledHandler is None:
			import led_handler
			self._ledHandler = led_handler.LedHandler()
		return self._ledHandler

	def _new_main_window(self):
		return MainWindow(None, self)

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_about(self, checked = True):
		with qui_utils.notify_error(self._errorLog):
			if self._aboutDialog is None:
				import dialogs
				self._aboutDialog = dialogs.AboutDialog(self)
			response = self._aboutDialog.run(self._mainWindow.window)


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

	@property
	def child(self):
		return self._child

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


class MainWindow(qwrappers.WindowWrapper):

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
		qwrappers.WindowWrapper.__init__(self, parent, app)
		self._window.setWindowTitle("%s" % constants.__pretty_app_name__)
		self._errorLog = self._app.errorLog

		self._session = session.Session(self._errorLog, constants._data_path_)
		self._session.error.connect(self._on_session_error)
		self._session.loggedIn.connect(self._on_login)
		self._session.loggedOut.connect(self._on_logout)
		self._session.draft.recipientsChanged.connect(self._on_recipients_changed)
		self._session.newMessages.connect(self._on_new_message_alert)
		self._app.alarmHandler.applicationNotifySignal.connect(self._on_app_alert)
		self._voicemailRefreshDelay = QtCore.QTimer()
		self._voicemailRefreshDelay.setInterval(30 * 1000)
		self._voicemailRefreshDelay.timeout.connect(self._on_call_missed)
		self._voicemailRefreshDelay.setSingleShot(True)
		self._callHandler = None
		self._updateVoicemailOnMissedCall = False

		self._defaultCredentials = "", ""
		self._curentCredentials = "", ""
		self._currentTab = 0

		self._credentialsDialog = None
		self._smsEntryDialog = None
		self._accountDialog = None

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
		defaultTabIconSize = self._tabWidget.iconSize()
		defaultTabIconWidth, defaultTabIconHeight = defaultTabIconSize.width(), defaultTabIconSize.height()
		for tabIndex, (tabTitle, tabIcon) in enumerate(
			zip(self._TAB_TITLES, self._TAB_ICONS)
		):
			icon = self._app.get_icon(tabIcon)
			if constants.IS_MAEMO and icon is not None:
				tabTitle = ""

			if icon is None:
				self._tabWidget.addTab(self._tabsContents[tabIndex].toplevel, tabTitle)
			else:
				iconSize = icon.availableSizes()[0]
				defaultTabIconWidth = max(defaultTabIconWidth, iconSize.width())
				defaultTabIconHeight = max(defaultTabIconHeight, iconSize.height())
				self._tabWidget.addTab(self._tabsContents[tabIndex].toplevel, icon, tabTitle)
		defaultTabIconWidth = max(defaultTabIconWidth, 32)
		defaultTabIconHeight = max(defaultTabIconHeight, 32)
		self._tabWidget.setIconSize(QtCore.QSize(defaultTabIconWidth, defaultTabIconHeight))
		self._tabWidget.currentChanged.connect(self._on_tab_changed)
		self._tabWidget.setContentsMargins(0, 0, 0, 0)

		self._layout.addWidget(self._tabWidget)

		self._loginAction = QtGui.QAction(None)
		self._loginAction.setText("Login")
		self._loginAction.triggered.connect(self._on_login_requested)

		self._importAction = QtGui.QAction(None)
		self._importAction.setText("Import")
		self._importAction.triggered.connect(self._on_import)

		self._accountAction = QtGui.QAction(None)
		self._accountAction.setText("Account")
		self._accountAction.triggered.connect(self._on_account)

		self._refreshConnectionAction = QtGui.QAction(None)
		self._refreshConnectionAction.setText("Refresh Connection")
		self._refreshConnectionAction.setShortcut(QtGui.QKeySequence("CTRL+a"))
		self._refreshConnectionAction.triggered.connect(self._on_refresh_connection)

		self._refreshTabAction = QtGui.QAction(None)
		self._refreshTabAction.setText("Refresh Tab")
		self._refreshTabAction.setShortcut(QtGui.QKeySequence("CTRL+r"))
		self._refreshTabAction.triggered.connect(self._on_refresh)

		fileMenu = self._window.menuBar().addMenu("&File")
		fileMenu.addAction(self._loginAction)
		fileMenu.addAction(self._refreshTabAction)
		fileMenu.addAction(self._refreshConnectionAction)

		toolsMenu = self._window.menuBar().addMenu("&Tools")
		toolsMenu.addAction(self._accountAction)
		toolsMenu.addAction(self._importAction)
		toolsMenu.addAction(self._app.aboutAction)

		self._initialize_tab(self._tabWidget.currentIndex())
		self.set_fullscreen(self._app.fullscreenAction.isChecked())
		self.set_orientation(self._app.orientationAction.isChecked())

	def set_default_credentials(self, username, password):
		self._defaultCredentials = username, password

	def get_default_credentials(self):
		return self._defaultCredentials

	def walk_children(self):
		if self._smsEntryDialog is not None:
			return (self._smsEntryDialog, )
		else:
			return ()

	def start(self):
		qwrappers.WindowWrapper.start(self)
		assert self._session.state == self._session.LOGGEDOUT_STATE, "Initialization messed up"
		if self._defaultCredentials != ("", ""):
			username, password = self._defaultCredentials[0], self._defaultCredentials[1]
			self._curentCredentials = username, password
			self._session.login(username, password)
		else:
			self._prompt_for_login()

	def close(self):
		for diag in (
			self._credentialsDialog,
			self._accountDialog,
		):
			if diag is not None:
				diag.close()
		for child in self.walk_children():
			child.window.destroyed.disconnect(self._on_child_close)
			child.window.closed.disconnect(self._on_child_close)
			child.close()
		self._window.close()

	def destroy(self):
		qwrappers.WindowWrapper.destroy(self)
		if self._session.state != self._session.LOGGEDOUT_STATE:
			self._session.logout()

	def get_current_tab(self):
		return self._currentTab

	def set_current_tab(self, tabIndex):
		self._tabWidget.setCurrentIndex(tabIndex)

	def load_settings(self, config):
		blobs = "", ""
		isFullscreen = False
		isPortrait = qui_utils.screen_orientation() == QtCore.Qt.Vertical
		tabIndex = 0
		try:
			blobs = [
				config.get(constants.__pretty_app_name__, "bin_blob_%i" % i)
				for i in xrange(len(self.get_default_credentials()))
			]
			isFullscreen = config.getboolean(constants.__pretty_app_name__, "fullscreen")
			tabIndex = config.getint(constants.__pretty_app_name__, "tab")
			isPortrait = config.getboolean(constants.__pretty_app_name__, "portrait")
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
		except Exception:
			_moduleLogger.exception("Unknown loading error")

		try:
			self._app.alarmHandler.load_settings(config, "alarm")
			self._app.notifyOnMissed = config.getboolean("2 - Account Info", "notifyOnMissed")
			self._app.notifyOnVoicemail = config.getboolean("2 - Account Info", "notifyOnVoicemail")
			self._app.notifyOnSms = config.getboolean("2 - Account Info", "notifyOnSms")
			self._updateVoicemailOnMissedCall = config.getboolean("2 - Account Info", "updateVoicemailOnMissedCall")
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
		except Exception:
			_moduleLogger.exception("Unknown loading error")

		creds = (
			base64.b64decode(blob)
			for blob in blobs
		)
		self.set_default_credentials(*creds)
		self._app.fullscreenAction.setChecked(isFullscreen)
		self._app.orientationAction.setChecked(isPortrait)
		self.set_current_tab(tabIndex)

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
		config.add_section(constants.__pretty_app_name__)
		config.set(constants.__pretty_app_name__, "tab", str(self.get_current_tab()))
		config.set(constants.__pretty_app_name__, "fullscreen", str(self._app.fullscreenAction.isChecked()))
		config.set(constants.__pretty_app_name__, "portrait", str(self._app.orientationAction.isChecked()))
		for i, value in enumerate(self.get_default_credentials()):
			blob = base64.b64encode(value)
			config.set(constants.__pretty_app_name__, "bin_blob_%i" % i, blob)

		config.add_section("alarm")
		self._app.alarmHandler.save_settings(config, "alarm")
		config.add_section("2 - Account Info")
		config.set("2 - Account Info", "notifyOnMissed", repr(self._app.notifyOnMissed))
		config.set("2 - Account Info", "notifyOnVoicemail", repr(self._app.notifyOnVoicemail))
		config.set("2 - Account Info", "notifyOnSms", repr(self._app.notifyOnSms))
		config.set("2 - Account Info", "updateVoicemailOnMissedCall", repr(self._updateVoicemailOnMissedCall))

		backendId = 2 # For backwards compatibility
		for tabIndex, tabTitle in enumerate(self._TAB_TITLES):
			sectionName = "%s - %s" % (backendId, tabTitle)
			config.add_section(sectionName)
			tabSettings = self._tabsContents[tabIndex].get_settings()
			for settingName, settingValue in tabSettings.iteritems():
				config.set(sectionName, settingName, settingValue)

	def set_orientation(self, isPortrait):
		qwrappers.WindowWrapper.set_orientation(self, isPortrait)
		if isPortrait:
			self._tabWidget.setTabPosition(QtGui.QTabWidget.South)
		else:
			self._tabWidget.setTabPosition(QtGui.QTabWidget.West)

	def _initialize_tab(self, index):
		assert index < self.MAX_TABS, "Invalid tab"
		if not self._tabsContents[index].has_child():
			tab = self._TAB_CLASS[index](self._app, self._session, self._errorLog)
			self._tabsContents[index].set_child(tab)
		self._tabsContents[index].refresh(force=False)

	def _prompt_for_login(self):
		if self._credentialsDialog is None:
			import dialogs
			self._credentialsDialog = dialogs.CredentialsDialog(self._app)
		credentials = self._credentialsDialog.run(
			self._defaultCredentials[0], self._defaultCredentials[1], self.window
		)
		if credentials is None:
			return
		username, password = credentials
		self._curentCredentials = username, password
		self._session.login(username, password)

	def _show_account_dialog(self):
		if self._accountDialog is None:
			import dialogs
			self._accountDialog = dialogs.AccountDialog(self._app)
			self._accountDialog.setIfNotificationsSupported(self._app.alarmHandler.backgroundNotificationsSupported)

		if self._callHandler is None or not self._callHandler.isSupported:
			self._accountDialog.updateVMOnMissedCall = self._accountDialog.VOICEMAIL_CHECK_NOT_SUPPORTED
		elif self._updateVoicemailOnMissedCall:
			self._accountDialog.updateVMOnMissedCall = self._accountDialog.VOICEMAIL_CHECK_ENABLED
		else:
			self._accountDialog.updateVMOnMissedCall = self._accountDialog.VOICEMAIL_CHECK_DISABLED
		self._accountDialog.notifications = self._app.alarmHandler.alarmType
		self._accountDialog.notificationTime = self._app.alarmHandler.recurrence
		self._accountDialog.notifyOnMissed = self._app.notifyOnMissed
		self._accountDialog.notifyOnVoicemail = self._app.notifyOnVoicemail
		self._accountDialog.notifyOnSms = self._app.notifyOnSms
		self._accountDialog.set_callbacks(
			self._session.get_callback_numbers(), self._session.get_callback_number()
		)
		accountNumberToDisplay = self._session.get_account_number()
		if not accountNumberToDisplay:
			accountNumberToDisplay = "Not Available (%s)" % self._session.state
		self._accountDialog.set_account_number(accountNumberToDisplay)
		response = self._accountDialog.run(self.window)
		if response == QtGui.QDialog.Accepted:
			if self._accountDialog.doClear:
				self._session.logout_and_clear()
				self._defaultCredentials = "", ""
				self._curentCredentials = "", ""
				for tab in self._tabsContents:
					tab.disable()
			else:
				callbackNumber = self._accountDialog.selectedCallback
				self._session.set_callback_number(callbackNumber)

			if self._callHandler is None or self._accountDialog.updateVMOnMissedCall == self._accountDialog.VOICEMAIL_CHECK_DISABLEDD:
				pass
			elif self._accountDialog.updateVMOnMissedCall == self._accountDialog.VOICEMAIL_CHECK_ENABLED:
				self._updateVoicemailOnMissedCall = True
				self._callHandler.start()
			else:
				self._updateVoicemailOnMissedCall = False
				self._callHandler.stop()
			if (
				self._accountDialog.notifyOnMissed or
				self._accountDialog.notifyOnVoicemail or
				self._accountDialog.notifyOnSms
			):
				notifications = self._accountDialog.notifications
			else:
				notifications = self._accountDialog.ALARM_NONE
			self._app.alarmHandler.apply_settings(notifications, self._accountDialog.notificationTime)

			self._app.notifyOnMissed = self._accountDialog.notifyOnMissed
			self._app.notifyOnVoicemail = self._accountDialog.notifyOnVoicemail
			self._app.notifyOnSms = self._accountDialog.notifyOnSms
			self._app.save_settings()
		elif response == QtGui.QDialog.Rejected:
			_moduleLogger.info("Cancelled")
		else:
			_moduleLogger.info("Unknown response")

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_new_message_alert(self):
		with qui_utils.notify_error(self._errorLog):
			if self._app.alarmHandler.alarmType == self._app.alarmHandler.ALARM_APPLICATION:
				if self._currentTab == self.MESSAGES_TAB or not self._app.ledHandler.isReal:
					self._errorLog.push_message("New messages available")
				else:
					self._app.ledHandler.on()

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_call_missed(self):
		with qui_utils.notify_error(self._errorLog):
			self._session.update_messages(self._session.MESSAGE_VOICEMAILS, force=True)

	@QtCore.pyqtSlot(str)
	@misc_utils.log_exception(_moduleLogger)
	def _on_session_error(self, message):
		with qui_utils.notify_error(self._errorLog):
			self._errorLog.push_error(message)

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_login(self):
		with qui_utils.notify_error(self._errorLog):
			changedAccounts = self._defaultCredentials != self._curentCredentials
			noCallback = not self._session.get_callback_number()
			if changedAccounts or noCallback:
				self._show_account_dialog()

			self._defaultCredentials = self._curentCredentials

			for tab in self._tabsContents:
				tab.enable()
			self._initialize_tab(self._currentTab)
			if self._updateVoicemailOnMissedCall:
				if self._callHandler is None:
					import call_handler
					self._callHandler = call_handler.MissedCallWatcher()
					self._callHandler.callMissed.connect(self._voicemailRefreshDelay.start)
				self._callHandler.start()

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_logout(self):
		with qui_utils.notify_error(self._errorLog):
			for tab in self._tabsContents:
				tab.disable()
			if self._callHandler is not None:
				self._callHandler.stop()

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_app_alert(self):
		with qui_utils.notify_error(self._errorLog):
			if self._session.state == self._session.LOGGEDIN_STATE:
				messageType = {
					(True, True): self._session.MESSAGE_ALL,
					(True, False): self._session.MESSAGE_TEXTS,
					(False, True): self._session.MESSAGE_VOICEMAILS,
				}[(self._app.notifyOnSms, self._app.notifyOnVoicemail)]
				self._session.update_messages(messageType, force=True)

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_recipients_changed(self):
		with qui_utils.notify_error(self._errorLog):
			if self._session.draft.get_num_contacts() == 0:
				return

			if self._smsEntryDialog is None:
				import dialogs
				self._smsEntryDialog = dialogs.SMSEntryWindow(self.window, self._app, self._session, self._errorLog)
				self._smsEntryDialog.window.destroyed.connect(self._on_child_close)
				self._smsEntryDialog.window.closed.connect(self._on_child_close)
				self._smsEntryDialog.window.show()

	@misc_utils.log_exception(_moduleLogger)
	def _on_child_close(self, obj = None):
		self._smsEntryDialog = None

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_login_requested(self, checked = True):
		with qui_utils.notify_error(self._errorLog):
			self._prompt_for_login()

	@QtCore.pyqtSlot(int)
	@misc_utils.log_exception(_moduleLogger)
	def _on_tab_changed(self, index):
		with qui_utils.notify_error(self._errorLog):
			self._currentTab = index
			self._initialize_tab(index)
			if self._app.alarmHandler.alarmType == self._app.alarmHandler.ALARM_APPLICATION:
				self._app.ledHandler.off()

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_refresh(self, checked = True):
		with qui_utils.notify_error(self._errorLog):
			self._tabsContents[self._currentTab].refresh(force=True)

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_refresh_connection(self, checked = True):
		with qui_utils.notify_error(self._errorLog):
			self._session.refresh_connection()

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_import(self, checked = True):
		with qui_utils.notify_error(self._errorLog):
			csvName = QtGui.QFileDialog.getOpenFileName(self._window, caption="Import", filter="CSV Files (*.csv)")
			csvName = unicode(csvName)
			if not csvName:
				return
			import shutil
			shutil.copy2(csvName, self._app.fsContactsPath)
			if self._tabsContents[self.CONTACTS_TAB].has_child:
				self._tabsContents[self.CONTACTS_TAB].child.update_addressbooks()

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_account(self, checked = True):
		with qui_utils.notify_error(self._errorLog):
			assert self._session.state == self._session.LOGGEDIN_STATE, "Must be logged in for settings"
			self._show_account_dialog()


def run():
	try:
		os.makedirs(constants._data_path_)
	except OSError, e:
		if e.errno != 17:
			raise

	logFormat = '(%(relativeCreated)5d) %(levelname)-5s %(threadName)s.%(name)s.%(funcName)s: %(message)s'
	logging.basicConfig(level=logging.DEBUG, format=logFormat)
	rotating = logging.handlers.RotatingFileHandler(constants._user_logpath_, maxBytes=512*1024, backupCount=1)
	rotating.setFormatter(logging.Formatter(logFormat))
	root = logging.getLogger()
	root.addHandler(rotating)
	_moduleLogger.info("%s %s-%s" % (constants.__app_name__, constants.__version__, constants.__build__))
	_moduleLogger.info("OS: %s" % (os.uname()[0], ))
	_moduleLogger.info("Kernel: %s (%s) for %s" % os.uname()[2:])
	_moduleLogger.info("Hostname: %s" % os.uname()[1])

	try:
		import gobject
		gobject.threads_init()
	except ImportError:
		_moduleLogger.info("GObject support not available")
	try:
		import dbus
		try:
			from dbus.mainloop.qt import DBusQtMainLoop
			DBusQtMainLoop(set_as_default=True)
			_moduleLogger.info("Using Qt mainloop")
		except ImportError:
			try:
				from dbus.mainloop.glib import DBusGMainLoop
				DBusGMainLoop(set_as_default=True)
				_moduleLogger.info("Using GObject mainloop")
			except ImportError:
				_moduleLogger.info("Mainloop not available")
	except ImportError:
		_moduleLogger.info("DBus support not available")

	app = QtGui.QApplication([])
	handle = Dialcentral(app)
	qtpie.init_pies()
	return app.exec_()


if __name__ == "__main__":
	import sys

	val = run()
	sys.exit(val)
