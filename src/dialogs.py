#!/usr/bin/env python

from __future__ import with_statement
from __future__ import division

import functools
import copy
import logging

from PyQt4 import QtGui
from PyQt4 import QtCore

import constants
from util import qwrappers
from util import qui_utils
from util import misc as misc_utils


_moduleLogger = logging.getLogger(__name__)


class CredentialsDialog(object):

	def __init__(self, app):
		self._app = app
		self._usernameField = QtGui.QLineEdit()
		self._passwordField = QtGui.QLineEdit()
		self._passwordField.setEchoMode(QtGui.QLineEdit.Password)

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
				return None
			else:
				_moduleLogger.error("Unknown response")
				return None
		finally:
			self._dialog.setParent(None, QtCore.Qt.Dialog)

	def close(self):
		try:
			self._dialog.reject()
		except RuntimeError:
			_moduleLogger.exception("Oh well")

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_close_window(self, checked = True):
		with qui_utils.notify_error(self._app.errorLog):
			self._dialog.reject()


class AboutDialog(object):

	def __init__(self, app):
		self._app = app
		self._title = QtGui.QLabel(
			"<h1>%s</h1><h3>Version: %s</h3>" % (
				constants.__pretty_app_name__, constants.__version__
			)
		)
		self._title.setTextFormat(QtCore.Qt.RichText)
		self._title.setAlignment(QtCore.Qt.AlignCenter)
		self._copyright = QtGui.QLabel("<h6>Developed by Ed Page<h6><h6>Icons: See website</h6>")
		self._copyright.setTextFormat(QtCore.Qt.RichText)
		self._copyright.setAlignment(QtCore.Qt.AlignCenter)
		self._link = QtGui.QLabel('<a href="http://gc-dialer.garage.maemo.org">DialCentral Website</a>')
		self._link.setTextFormat(QtCore.Qt.RichText)
		self._link.setAlignment(QtCore.Qt.AlignCenter)
		self._link.setOpenExternalLinks(True)

		self._buttonLayout = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Cancel)

		self._layout = QtGui.QVBoxLayout()
		self._layout.addWidget(self._title)
		self._layout.addWidget(self._copyright)
		self._layout.addWidget(self._link)
		self._layout.addWidget(self._buttonLayout)

		self._dialog = QtGui.QDialog()
		self._dialog.setWindowTitle("About")
		self._dialog.setLayout(self._layout)
		self._buttonLayout.rejected.connect(self._dialog.reject)

		self._closeWindowAction = QtGui.QAction(None)
		self._closeWindowAction.setText("Close")
		self._closeWindowAction.setShortcut(QtGui.QKeySequence("CTRL+w"))
		self._closeWindowAction.triggered.connect(self._on_close_window)

		self._dialog.addAction(self._closeWindowAction)
		self._dialog.addAction(app.quitAction)
		self._dialog.addAction(app.fullscreenAction)

	def run(self, parent=None):
		self._dialog.setParent(parent, QtCore.Qt.Dialog)

		response = self._dialog.exec_()
		return response

	def close(self):
		try:
			self._dialog.reject()
		except RuntimeError:
			_moduleLogger.exception("Oh well")

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_close_window(self, checked = True):
		with qui_utils.notify_error(self._app.errorLog):
			self._dialog.reject()


class AccountDialog(object):

	# @bug Can't enter custom callback numbers

	_RECURRENCE_CHOICES = [
		(1, "1 minute"),
		(2, "2 minutes"),
		(3, "3 minutes"),
		(5, "5 minutes"),
		(8, "8 minutes"),
		(10, "10 minutes"),
		(15, "15 minutes"),
		(30, "30 minutes"),
		(45, "45 minutes"),
		(60, "1 hour"),
		(3*60, "3 hours"),
		(6*60, "6 hours"),
		(12*60, "12 hours"),
	]

	ALARM_NONE = "No Alert"
	ALARM_BACKGROUND = "Background Alert"
	ALARM_APPLICATION = "Application Alert"

	VOICEMAIL_CHECK_NOT_SUPPORTED = "Not Supported"
	VOICEMAIL_CHECK_DISABLED = "Disabled"
	VOICEMAIL_CHECK_ENABLED = "Enabled"

	def __init__(self, app):
		self._app = app
		self._doClear = False

		self._accountNumberLabel = QtGui.QLabel("NUMBER NOT SET")
		self._notificationSelecter = QtGui.QComboBox()
		self._notificationSelecter.currentIndexChanged.connect(self._on_notification_change)
		self._notificationTimeSelector = QtGui.QComboBox()
		#self._notificationTimeSelector.setEditable(True)
		self._notificationTimeSelector.setInsertPolicy(QtGui.QComboBox.InsertAtTop)
		for _, label in self._RECURRENCE_CHOICES:
			self._notificationTimeSelector.addItem(label)
		self._missedCallsNotificationButton = QtGui.QCheckBox("Missed Calls")
		self._voicemailNotificationButton = QtGui.QCheckBox("Voicemail")
		self._smsNotificationButton = QtGui.QCheckBox("SMS")
		self._voicemailOnMissedButton = QtGui.QCheckBox("Voicemail Update on Missed Calls")
		self._clearButton = QtGui.QPushButton("Clear Account")
		self._clearButton.clicked.connect(self._on_clear)
		self._callbackSelector = QtGui.QComboBox()
		#self._callbackSelector.setEditable(True)
		self._callbackSelector.setInsertPolicy(QtGui.QComboBox.InsertAtTop)

		self._update_notification_state()

		self._credLayout = QtGui.QGridLayout()
		self._credLayout.addWidget(QtGui.QLabel("Account"), 0, 0)
		self._credLayout.addWidget(self._accountNumberLabel, 0, 1)
		self._credLayout.addWidget(QtGui.QLabel("Callback"), 1, 0)
		self._credLayout.addWidget(self._callbackSelector, 1, 1)
		self._credLayout.addWidget(self._notificationSelecter, 2, 0)
		self._credLayout.addWidget(self._notificationTimeSelector, 2, 1)
		self._credLayout.addWidget(QtGui.QLabel(""), 3, 0)
		self._credLayout.addWidget(self._missedCallsNotificationButton, 3, 1)
		self._credLayout.addWidget(QtGui.QLabel(""), 4, 0)
		self._credLayout.addWidget(self._voicemailNotificationButton, 4, 1)
		self._credLayout.addWidget(QtGui.QLabel(""), 5, 0)
		self._credLayout.addWidget(self._smsNotificationButton, 5, 1)
		self._credLayout.addWidget(QtGui.QLabel(""), 6, 0)
		self._credLayout.addWidget(self._voicemailOnMissedButton, 6, 1)

		self._credLayout.addWidget(QtGui.QLabel(""), 7, 0)
		self._credLayout.addWidget(self._clearButton, 7, 1)

		self._loginButton = QtGui.QPushButton("&Apply")
		self._buttonLayout = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Cancel)
		self._buttonLayout.addButton(self._loginButton, QtGui.QDialogButtonBox.AcceptRole)

		self._layout = QtGui.QVBoxLayout()
		self._layout.addLayout(self._credLayout)
		self._layout.addWidget(self._buttonLayout)

		self._dialog = QtGui.QDialog()
		self._dialog.setWindowTitle("Account")
		self._dialog.setLayout(self._layout)
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

	def setIfNotificationsSupported(self, isSupported):
		if isSupported:
			self._notificationSelecter.clear()
			self._notificationSelecter.addItems([self.ALARM_NONE, self.ALARM_APPLICATION, self.ALARM_BACKGROUND])
			self._notificationTimeSelector.setEnabled(False)
			self._missedCallsNotificationButton.setEnabled(False)
			self._voicemailNotificationButton.setEnabled(False)
			self._smsNotificationButton.setEnabled(False)
		else:
			self._notificationSelecter.clear()
			self._notificationSelecter.addItems([self.ALARM_NONE, self.ALARM_APPLICATION])
			self._notificationTimeSelector.setEnabled(False)
			self._missedCallsNotificationButton.setEnabled(False)
			self._voicemailNotificationButton.setEnabled(False)
			self._smsNotificationButton.setEnabled(False)

	def set_account_number(self, num):
		self._accountNumberLabel.setText(num)

	def _set_voicemail_on_missed(self, status):
		if status == self.VOICEMAIL_CHECK_NOT_SUPPORTED:
			self._voicemailOnMissedButton.setChecked(False)
			self._voicemailOnMissedButton.hide()
		elif status == self.VOICEMAIL_CHECK_DISABLED:
			self._voicemailOnMissedButton.setChecked(False)
			self._voicemailOnMissedButton.show()
		elif status == self.VOICEMAIL_CHECK_ENABLED:
			self._voicemailOnMissedButton.setChecked(True)
			self._voicemailOnMissedButton.show()
		else:
			raise RuntimeError("Unsupported option for updating voicemail on missed calls %r" % status)

	def _get_voicemail_on_missed(self):
		if not self._voicemailOnMissedButton.isVisible():
			return self.VOICEMAIL_CHECK_NOT_SUPPORTED
		elif self._voicemailOnMissedButton.isChecked():
			return self.VOICEMAIL_CHECK_ENABLED
		else:
			return self.VOICEMAIL_CHECK_DISABLED

	updateVMOnMissedCall = property(_get_voicemail_on_missed, _set_voicemail_on_missed)

	def _set_notifications(self, enabled):
		for i in xrange(self._notificationSelecter.count()):
			if self._notificationSelecter.itemText(i) == enabled:
				self._notificationSelecter.setCurrentIndex(i)
				break
		else:
			self._notificationSelecter.setCurrentIndex(0)

	notifications = property(
		lambda self: str(self._notificationSelecter.currentText()),
		_set_notifications,
	)

	notifyOnMissed = property(
		lambda self: self._missedCallsNotificationButton.isChecked(),
		lambda self, enabled: self._missedCallsNotificationButton.setChecked(enabled),
	)

	notifyOnVoicemail = property(
		lambda self: self._voicemailNotificationButton.isChecked(),
		lambda self, enabled: self._voicemailNotificationButton.setChecked(enabled),
	)

	notifyOnSms = property(
		lambda self: self._smsNotificationButton.isChecked(),
		lambda self, enabled: self._smsNotificationButton.setChecked(enabled),
	)

	def _get_notification_time(self):
		index = self._notificationTimeSelector.currentIndex()
		minutes = self._RECURRENCE_CHOICES[index][0]
		return minutes

	def _set_notification_time(self, minutes):
		for i, (time, _) in enumerate(self._RECURRENCE_CHOICES):
			if time == minutes:
				self._notificationTimeSelector.setCurrentIndex(i)
				break
		else:
				self._notificationTimeSelector.setCurrentIndex(0)

	notificationTime = property(_get_notification_time, _set_notification_time)

	@property
	def selectedCallback(self):
		index = self._callbackSelector.currentIndex()
		data = str(self._callbackSelector.itemData(index).toPyObject())
		return data

	def set_callbacks(self, choices, default):
		self._callbackSelector.clear()

		self._callbackSelector.addItem("Not Set", "")

		uglyDefault = misc_utils.make_ugly(default)
		for number, description in choices.iteritems():
			prettyNumber = misc_utils.make_pretty(number)
			uglyNumber = misc_utils.make_ugly(number)
			if not uglyNumber:
				continue

			self._callbackSelector.addItem("%s - %s" % (prettyNumber, description), uglyNumber)
			if uglyNumber == uglyDefault:
				self._callbackSelector.setCurrentIndex(self._callbackSelector.count() - 1)

	def run(self, parent=None):
		self._doClear = False
		self._dialog.setParent(parent, QtCore.Qt.Dialog)

		response = self._dialog.exec_()
		return response

	def close(self):
		try:
			self._dialog.reject()
		except RuntimeError:
			_moduleLogger.exception("Oh well")

	def _update_notification_state(self):
		currentText = str(self._notificationSelecter.currentText())
		if currentText == self.ALARM_BACKGROUND:
			self._notificationTimeSelector.setEnabled(True)

			self._missedCallsNotificationButton.setEnabled(True)
			self._voicemailNotificationButton.setEnabled(True)
			self._smsNotificationButton.setEnabled(True)
		elif currentText == self.ALARM_APPLICATION:
			self._notificationTimeSelector.setEnabled(True)

			self._missedCallsNotificationButton.setEnabled(False)
			self._voicemailNotificationButton.setEnabled(True)
			self._smsNotificationButton.setEnabled(True)

			self._missedCallsNotificationButton.setChecked(False)
		else:
			self._notificationTimeSelector.setEnabled(False)

			self._missedCallsNotificationButton.setEnabled(False)
			self._voicemailNotificationButton.setEnabled(False)
			self._smsNotificationButton.setEnabled(False)

			self._missedCallsNotificationButton.setChecked(False)
			self._voicemailNotificationButton.setChecked(False)
			self._smsNotificationButton.setChecked(False)

	@QtCore.pyqtSlot(int)
	@misc_utils.log_exception(_moduleLogger)
	def _on_notification_change(self, index):
		with qui_utils.notify_error(self._app.errorLog):
			self._update_notification_state()

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_clear(self, checked = False):
		with qui_utils.notify_error(self._app.errorLog):
			self._doClear = True
			self._dialog.accept()

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_close_window(self, checked = True):
		with qui_utils.notify_error(self._app.errorLog):
			self._dialog.reject()


class ContactList(object):

	_SENTINEL_ICON = QtGui.QIcon()

	def __init__(self, app, session):
		self._app = app
		self._session = session
		self._targetLayout = QtGui.QVBoxLayout()
		self._targetList = QtGui.QWidget()
		self._targetList.setLayout(self._targetLayout)
		self._uiItems = []
		self._closeIcon = qui_utils.get_theme_icon(("window-close", "general_close", "gtk-close"), self._SENTINEL_ICON)

	@property
	def toplevel(self):
		return self._targetList

	def setVisible(self, isVisible):
		self._targetList.setVisible(isVisible)

	def update(self):
		cids = list(self._session.draft.get_contacts())
		amountCommon = min(len(cids), len(self._uiItems))

		# Run through everything in common
		for i in xrange(0, amountCommon):
			cid = cids[i]
			uiItem = self._uiItems[i]
			title = self._session.draft.get_title(cid)
			description = self._session.draft.get_description(cid)
			numbers = self._session.draft.get_numbers(cid)
			uiItem["cid"] = cid
			uiItem["title"] = title
			uiItem["description"] = description
			uiItem["numbers"] = numbers
			uiItem["label"].setText(title)
			self._populate_number_selector(uiItem["selector"], cid, i, numbers)
			uiItem["rowWidget"].setVisible(True)

		# More contacts than ui items
		for i in xrange(amountCommon, len(cids)):
			cid = cids[i]
			title = self._session.draft.get_title(cid)
			description = self._session.draft.get_description(cid)
			numbers = self._session.draft.get_numbers(cid)

			titleLabel = QtGui.QLabel(title)
			titleLabel.setWordWrap(True)
			numberSelector = QtGui.QComboBox()
			self._populate_number_selector(numberSelector, cid, i, numbers)

			callback = functools.partial(
				self._on_change_number,
				i
			)
			callback.__name__ = "thanks partials for not having names and pyqt for requiring them"
			numberSelector.activated.connect(
				QtCore.pyqtSlot(int)(callback)
			)

			if self._closeIcon is self._SENTINEL_ICON:
				deleteButton = QtGui.QPushButton("Delete")
			else:
				deleteButton = QtGui.QPushButton(self._closeIcon, "")
			deleteButton.setSizePolicy(QtGui.QSizePolicy(
				QtGui.QSizePolicy.Minimum,
				QtGui.QSizePolicy.Minimum,
				QtGui.QSizePolicy.PushButton,
			))
			callback = functools.partial(
				self._on_remove_contact,
				i
			)
			callback.__name__ = "thanks partials for not having names and pyqt for requiring them"
			deleteButton.clicked.connect(callback)

			rowLayout = QtGui.QHBoxLayout()
			rowLayout.addWidget(titleLabel, 1000)
			rowLayout.addWidget(numberSelector, 0)
			rowLayout.addWidget(deleteButton, 0)
			rowWidget = QtGui.QWidget()
			rowWidget.setLayout(rowLayout)
			self._targetLayout.addWidget(rowWidget)

			uiItem = {}
			uiItem["cid"] = cid
			uiItem["title"] = title
			uiItem["description"] = description
			uiItem["numbers"] = numbers
			uiItem["label"] = titleLabel
			uiItem["selector"] = numberSelector
			uiItem["rowWidget"] = rowWidget
			self._uiItems.append(uiItem)
			amountCommon = i+1

		# More UI items than contacts
		for i in xrange(amountCommon, len(self._uiItems)):
			uiItem = self._uiItems[i]
			uiItem["rowWidget"].setVisible(False)
			amountCommon = i+1

	def _populate_number_selector(self, selector, cid, cidIndex, numbers):
		selector.clear()

		selectedNumber = self._session.draft.get_selected_number(cid)
		if len(numbers) == 1:
			# If no alt numbers available, check the address book
			numbers, defaultIndex = _get_contact_numbers(self._session, cid, selectedNumber, numbers[0][1])
		else:
			defaultIndex = _index_number(numbers, selectedNumber)

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

	@misc_utils.log_exception(_moduleLogger)
	def _on_change_number(self, cidIndex, index):
		with qui_utils.notify_error(self._app.errorLog):
			# Exception thrown when the first item is removed
			try:
				cid = self._uiItems[cidIndex]["cid"]
				numbers = self._session.draft.get_numbers(cid)
			except IndexError:
				_moduleLogger.error("Contact no longer available (or bizarre error): %r (%r)" % (cid, index))
				return
			except KeyError:
				_moduleLogger.error("Contact no longer available (or bizarre error): %r (%r)" % (cid, index))
				return
			number = numbers[index][0]
			self._session.draft.set_selected_number(cid, number)

	@misc_utils.log_exception(_moduleLogger)
	def _on_remove_contact(self, index, toggled):
		with qui_utils.notify_error(self._app.errorLog):
			self._session.draft.remove_contact(self._uiItems[index]["cid"])


class VoicemailPlayer(object):

	def __init__(self, app, session, errorLog):
		self._app = app
		self._session = session
		self._errorLog = errorLog
		self._token = None
		self._session.voicemailAvailable.connect(self._on_voicemail_downloaded)
		self._session.draft.recipientsChanged.connect(self._on_recipients_changed)

		self._playButton = QtGui.QPushButton("Play")
		self._playButton.clicked.connect(self._on_voicemail_play)
		self._pauseButton = QtGui.QPushButton("Pause")
		self._pauseButton.clicked.connect(self._on_voicemail_pause)
		self._pauseButton.hide()
		self._resumeButton = QtGui.QPushButton("Resume")
		self._resumeButton.clicked.connect(self._on_voicemail_resume)
		self._resumeButton.hide()
		self._stopButton = QtGui.QPushButton("Stop")
		self._stopButton.clicked.connect(self._on_voicemail_stop)
		self._stopButton.hide()

		self._downloadButton = QtGui.QPushButton("Download Voicemail")
		self._downloadButton.clicked.connect(self._on_voicemail_download)
		self._downloadLayout = QtGui.QHBoxLayout()
		self._downloadLayout.addWidget(self._downloadButton)
		self._downloadWidget = QtGui.QWidget()
		self._downloadWidget.setLayout(self._downloadLayout)

		self._playLabel = QtGui.QLabel("Voicemail")
		self._saveButton = QtGui.QPushButton("Save")
		self._saveButton.clicked.connect(self._on_voicemail_save)
		self._playerLayout = QtGui.QHBoxLayout()
		self._playerLayout.addWidget(self._playLabel)
		self._playerLayout.addWidget(self._playButton)
		self._playerLayout.addWidget(self._pauseButton)
		self._playerLayout.addWidget(self._resumeButton)
		self._playerLayout.addWidget(self._stopButton)
		self._playerLayout.addWidget(self._saveButton)
		self._playerWidget = QtGui.QWidget()
		self._playerWidget.setLayout(self._playerLayout)

		self._visibleWidget = None
		self._layout = QtGui.QHBoxLayout()
		self._layout.setContentsMargins(0, 0, 0, 0)
		self._widget = QtGui.QWidget()
		self._widget.setLayout(self._layout)
		self._update_state()

	@property
	def toplevel(self):
		return self._widget

	def destroy(self):
		self._session.voicemailAvailable.disconnect(self._on_voicemail_downloaded)
		self._session.draft.recipientsChanged.disconnect(self._on_recipients_changed)
		self._invalidate_token()

	def _invalidate_token(self):
		if self._token is not None:
			self._token.invalidate()
			self._token.error.disconnect(self._on_play_error)
			self._token.stateChange.connect(self._on_play_state)
			self._token.invalidated.connect(self._on_play_invalidated)

	def _show_download(self, messageId):
		if self._visibleWidget is self._downloadWidget:
			return
		self._hide()
		self._layout.addWidget(self._downloadWidget)
		self._visibleWidget = self._downloadWidget
		self._visibleWidget.show()

	def _show_player(self, messageId):
		if self._visibleWidget is self._playerWidget:
			return
		self._hide()
		self._layout.addWidget(self._playerWidget)
		self._visibleWidget = self._playerWidget
		self._visibleWidget.show()

	def _hide(self):
		if self._visibleWidget is None:
			return
		self._visibleWidget.hide()
		self._layout.removeWidget(self._visibleWidget)
		self._visibleWidget = None

	def _update_play_state(self):
		if self._token is not None and self._token.isValid:
			self._playButton.setText("Stop")
		else:
			self._playButton.setText("Play")

	def _update_state(self):
		if self._session.draft.get_num_contacts() != 1:
			self._hide()
			return

		(cid, ) = self._session.draft.get_contacts()
		messageId = self._session.draft.get_message_id(cid)
		if messageId is None:
			self._hide()
			return

		if self._session.is_available(messageId):
			self._show_player(messageId)
		else:
			self._show_download(messageId)
		if self._token is not None:
			self._token.invalidate()

	@misc_utils.log_exception(_moduleLogger)
	def _on_voicemail_save(self, arg):
		with qui_utils.notify_error(self._app.errorLog):
			targetPath = QtGui.QFileDialog.getSaveFileName(None, caption="Save Voicemail", filter="Audio File (*.mp3)")
			targetPath = unicode(targetPath)
			if not targetPath:
				return

			(cid, ) = self._session.draft.get_contacts()
			messageId = self._session.draft.get_message_id(cid)
			sourcePath = self._session.voicemail_path(messageId)
			import shutil
			shutil.copy2(sourcePath, targetPath)

	@misc_utils.log_exception(_moduleLogger)
	def _on_play_error(self, error):
		with qui_utils.notify_error(self._app.errorLog):
			self._app.errorLog.push_error(error)

	@misc_utils.log_exception(_moduleLogger)
	def _on_play_invalidated(self):
		with qui_utils.notify_error(self._app.errorLog):
			self._playButton.show()
			self._pauseButton.hide()
			self._resumeButton.hide()
			self._stopButton.hide()
			self._invalidate_token()

	@misc_utils.log_exception(_moduleLogger)
	def _on_play_state(self, state):
		with qui_utils.notify_error(self._app.errorLog):
			if state == self._token.STATE_PLAY:
				self._playButton.hide()
				self._pauseButton.show()
				self._resumeButton.hide()
				self._stopButton.show()
			elif state == self._token.STATE_PAUSE:
				self._playButton.hide()
				self._pauseButton.hide()
				self._resumeButton.show()
				self._stopButton.show()
			elif state == self._token.STATE_STOP:
				self._playButton.show()
				self._pauseButton.hide()
				self._resumeButton.hide()
				self._stopButton.hide()

	@misc_utils.log_exception(_moduleLogger)
	def _on_voicemail_play(self, arg):
		with qui_utils.notify_error(self._app.errorLog):
			(cid, ) = self._session.draft.get_contacts()
			messageId = self._session.draft.get_message_id(cid)
			sourcePath = self._session.voicemail_path(messageId)

			self._invalidate_token()
			uri = "file://%s" % sourcePath
			self._token = self._app.streamHandler.set_file(uri)
			self._token.stateChange.connect(self._on_play_state)
			self._token.invalidated.connect(self._on_play_invalidated)
			self._token.error.connect(self._on_play_error)
			self._token.play()

	@misc_utils.log_exception(_moduleLogger)
	def _on_voicemail_pause(self, arg):
		with qui_utils.notify_error(self._app.errorLog):
			self._token.pause()

	@misc_utils.log_exception(_moduleLogger)
	def _on_voicemail_resume(self, arg):
		with qui_utils.notify_error(self._app.errorLog):
			self._token.play()

	@misc_utils.log_exception(_moduleLogger)
	def _on_voicemail_stop(self, arg):
		with qui_utils.notify_error(self._app.errorLog):
			self._token.stop()

	@misc_utils.log_exception(_moduleLogger)
	def _on_voicemail_download(self, arg):
		with qui_utils.notify_error(self._app.errorLog):
			(cid, ) = self._session.draft.get_contacts()
			messageId = self._session.draft.get_message_id(cid)
			self._session.download_voicemail(messageId)
			self._hide()

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_recipients_changed(self):
		with qui_utils.notify_error(self._app.errorLog):
			self._update_state()

	@QtCore.pyqtSlot(str, str)
	@misc_utils.log_exception(_moduleLogger)
	def _on_voicemail_downloaded(self, messageId, filepath):
		with qui_utils.notify_error(self._app.errorLog):
			self._update_state()


class SMSEntryWindow(qwrappers.WindowWrapper):

	MAX_CHAR = 160
	# @bug Somehow a window is being destroyed on object creation which causes glitches on Maemo 5

	def __init__(self, parent, app, session, errorLog):
		qwrappers.WindowWrapper.__init__(self, parent, app)
		self._session = session
		self._session.messagesUpdated.connect(self._on_refresh_history)
		self._session.historyUpdated.connect(self._on_refresh_history)
		self._session.draft.recipientsChanged.connect(self._on_recipients_changed)

		self._session.draft.sendingMessage.connect(self._on_op_started)
		self._session.draft.calling.connect(self._on_op_started)
		self._session.draft.calling.connect(self._on_calling_started)
		self._session.draft.cancelling.connect(self._on_op_started)

		self._session.draft.sentMessage.connect(self._on_op_finished)
		self._session.draft.called.connect(self._on_op_finished)
		self._session.draft.cancelled.connect(self._on_op_finished)
		self._session.draft.error.connect(self._on_op_error)
		self._errorLog = errorLog

		self._errorDisplay = qui_utils.ErrorDisplay(self._errorLog)

		self._targetList = ContactList(self._app, self._session)
		self._history = QtGui.QLabel()
		self._history.setTextFormat(QtCore.Qt.RichText)
		self._history.setWordWrap(True)
		self._voicemailPlayer = VoicemailPlayer(self._app, self._session, self._errorLog)
		self._smsEntry = QtGui.QTextEdit()
		self._smsEntry.textChanged.connect(self._on_letter_count_changed)

		self._entryLayout = QtGui.QVBoxLayout()
		self._entryLayout.addWidget(self._targetList.toplevel)
		self._entryLayout.addWidget(self._history)
		self._entryLayout.addWidget(self._voicemailPlayer.toplevel, 0)
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

		self._characterCountLabel = QtGui.QLabel("")
		self._singleNumberSelector = QtGui.QComboBox()
		self._cids = []
		self._singleNumberSelector.activated.connect(self._on_single_change_number)
		self._smsButton = QtGui.QPushButton("SMS")
		self._smsButton.clicked.connect(self._on_sms_clicked)
		self._smsButton.setEnabled(False)
		self._dialButton = QtGui.QPushButton("Dial")
		self._dialButton.clicked.connect(self._on_call_clicked)
		self._cancelButton = QtGui.QPushButton("Cancel Call")
		self._cancelButton.clicked.connect(self._on_cancel_clicked)
		self._cancelButton.setVisible(False)

		self._buttonLayout = QtGui.QHBoxLayout()
		self._buttonLayout.addWidget(self._characterCountLabel)
		self._buttonLayout.addWidget(self._singleNumberSelector)
		self._buttonLayout.addWidget(self._smsButton)
		self._buttonLayout.addWidget(self._dialButton)
		self._buttonLayout.addWidget(self._cancelButton)

		self._layout.addWidget(self._errorDisplay.toplevel)
		self._layout.addWidget(self._scrollEntry)
		self._layout.addLayout(self._buttonLayout)
		self._layout.setDirection(QtGui.QBoxLayout.TopToBottom)

		self._window.setWindowTitle("Contact")
		self._window.closed.connect(self._on_close_window)
		self._window.hidden.connect(self._on_close_window)

		self._scrollTimer = QtCore.QTimer()
		self._scrollTimer.setInterval(100)
		self._scrollTimer.setSingleShot(True)
		self._scrollTimer.timeout.connect(self._on_delayed_scroll_to_bottom)

		self._smsEntry.setPlainText(self._session.draft.message)
		self._update_letter_count()
		self._update_target_fields()
		self.set_fullscreen(self._app.fullscreenAction.isChecked())
		self.set_orientation(self._app.orientationAction.isChecked())

	def close(self):
		if self._window is None:
			# Already closed
			return
		window = self._window
		try:
			message = unicode(self._smsEntry.toPlainText())
			self._session.draft.message = message
			self.hide()
		except AttributeError:
			_moduleLogger.exception("Oh well")
		except RuntimeError:
			_moduleLogger.exception("Oh well")

	def destroy(self):
		self._session.messagesUpdated.disconnect(self._on_refresh_history)
		self._session.historyUpdated.disconnect(self._on_refresh_history)
		self._session.draft.recipientsChanged.disconnect(self._on_recipients_changed)
		self._session.draft.sendingMessage.disconnect(self._on_op_started)
		self._session.draft.calling.disconnect(self._on_op_started)
		self._session.draft.calling.disconnect(self._on_calling_started)
		self._session.draft.cancelling.disconnect(self._on_op_started)
		self._session.draft.sentMessage.disconnect(self._on_op_finished)
		self._session.draft.called.disconnect(self._on_op_finished)
		self._session.draft.cancelled.disconnect(self._on_op_finished)
		self._session.draft.error.disconnect(self._on_op_error)
		self._voicemailPlayer.destroy()
		window = self._window
		self._window = None
		try:
			window.close()
			window.destroy()
		except AttributeError:
			_moduleLogger.exception("Oh well")
		except RuntimeError:
			_moduleLogger.exception("Oh well")

	def set_orientation(self, isPortrait):
		qwrappers.WindowWrapper.set_orientation(self, isPortrait)
		self._scroll_to_bottom()

	def _update_letter_count(self):
		count = self._smsEntry.toPlainText().size()
		numTexts, numCharInText = divmod(count, self.MAX_CHAR)
		numTexts += 1
		numCharsLeftInText = self.MAX_CHAR - numCharInText
		self._characterCountLabel.setText("%d (%d)" % (numCharsLeftInText, numTexts))

	def _update_button_state(self):
		self._cancelButton.setEnabled(True)
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
			count = self._smsEntry.toPlainText().size()
			if count == 0:
				self._smsButton.setEnabled(False)
			else:
				self._smsButton.setEnabled(True)

	def _update_history(self, cid):
		draftContactsCount = self._session.draft.get_num_contacts()
		if draftContactsCount != 1:
			self._history.setVisible(False)
		else:
			description = self._session.draft.get_description(cid)

			self._targetList.setVisible(False)
			if description:
				self._history.setText(description)
				self._history.setVisible(True)
			else:
				self._history.setText("")
				self._history.setVisible(False)

	def _update_target_fields(self):
		draftContactsCount = self._session.draft.get_num_contacts()
		if draftContactsCount == 0:
			self.hide()
			del self._cids[:]
		elif draftContactsCount == 1:
			(cid, ) = self._session.draft.get_contacts()
			title = self._session.draft.get_title(cid)
			numbers = self._session.draft.get_numbers(cid)

			self._targetList.setVisible(False)
			self._update_history(cid)
			self._populate_number_selector(self._singleNumberSelector, cid, 0, numbers)
			self._cids = [cid]

			self._scroll_to_bottom()
			self._window.setWindowTitle(title)
			self._smsEntry.setFocus(QtCore.Qt.OtherFocusReason)
			self.show()
			self._window.raise_()
		else:
			self._targetList.setVisible(True)
			self._targetList.update()
			self._history.setText("")
			self._history.setVisible(False)
			self._singleNumberSelector.setVisible(False)

			self._scroll_to_bottom()
			self._window.setWindowTitle("Contacts")
			self._smsEntry.setFocus(QtCore.Qt.OtherFocusReason)
			self.show()
			self._window.raise_()

	def _populate_number_selector(self, selector, cid, cidIndex, numbers):
		selector.clear()

		selectedNumber = self._session.draft.get_selected_number(cid)
		if len(numbers) == 1:
			# If no alt numbers available, check the address book
			numbers, defaultIndex = _get_contact_numbers(self._session, cid, selectedNumber, numbers[0][1])
		else:
			defaultIndex = _index_number(numbers, selectedNumber)

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

	def _scroll_to_bottom(self):
		self._scrollTimer.start()

	@misc_utils.log_exception(_moduleLogger)
	def _on_delayed_scroll_to_bottom(self):
		with qui_utils.notify_error(self._app.errorLog):
			self._scrollEntry.ensureWidgetVisible(self._smsEntry)

	@misc_utils.log_exception(_moduleLogger)
	def _on_sms_clicked(self, arg):
		with qui_utils.notify_error(self._app.errorLog):
			message = unicode(self._smsEntry.toPlainText())
			self._session.draft.message = message
			self._session.draft.send()

	@misc_utils.log_exception(_moduleLogger)
	def _on_call_clicked(self, arg):
		with qui_utils.notify_error(self._app.errorLog):
			message = unicode(self._smsEntry.toPlainText())
			self._session.draft.message = message
			self._session.draft.call()

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_cancel_clicked(self, message):
		with qui_utils.notify_error(self._app.errorLog):
			self._session.draft.cancel()

	@misc_utils.log_exception(_moduleLogger)
	def _on_single_change_number(self, index):
		with qui_utils.notify_error(self._app.errorLog):
			# Exception thrown when the first item is removed
			cid = self._cids[0]
			try:
				numbers = self._session.draft.get_numbers(cid)
			except KeyError:
				_moduleLogger.error("Contact no longer available (or bizarre error): %r (%r)" % (cid, index))
				return
			number = numbers[index][0]
			self._session.draft.set_selected_number(cid, number)

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_refresh_history(self):
		with qui_utils.notify_error(self._app.errorLog):
			draftContactsCount = self._session.draft.get_num_contacts()
			if draftContactsCount != 1:
				# Changing contact count will automatically refresh it
				return
			(cid, ) = self._session.draft.get_contacts()
			self._update_history(cid)

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_recipients_changed(self):
		with qui_utils.notify_error(self._app.errorLog):
			self._update_target_fields()
			self._update_button_state()

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_op_started(self):
		with qui_utils.notify_error(self._app.errorLog):
			self._smsEntry.setReadOnly(True)
			self._smsButton.setVisible(False)
			self._dialButton.setVisible(False)
			self.show()

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_calling_started(self):
		with qui_utils.notify_error(self._app.errorLog):
			self._cancelButton.setVisible(True)

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_op_finished(self):
		with qui_utils.notify_error(self._app.errorLog):
			self._smsEntry.setPlainText("")
			self._smsEntry.setReadOnly(False)
			self._cancelButton.setVisible(False)
			self._smsButton.setVisible(True)
			self._dialButton.setVisible(True)
			self.close()
			self.destroy()

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_op_error(self, message):
		with qui_utils.notify_error(self._app.errorLog):
			self._smsEntry.setReadOnly(False)
			self._cancelButton.setVisible(False)
			self._smsButton.setVisible(True)
			self._dialButton.setVisible(True)

			self._errorLog.push_error(message)

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_letter_count_changed(self):
		with qui_utils.notify_error(self._app.errorLog):
			self._update_letter_count()
			self._update_button_state()

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_close_window(self, checked = True):
		with qui_utils.notify_error(self._app.errorLog):
			self.close()


def _index_number(numbers, default):
	uglyDefault = misc_utils.make_ugly(default)
	uglyContactNumbers = list(
		misc_utils.make_ugly(contactNumber)
		for (contactNumber, _) in numbers
	)
	defaultMatches = [
		misc_utils.similar_ugly_numbers(uglyDefault, contactNumber)
		for contactNumber in uglyContactNumbers
	]
	try:
		defaultIndex = defaultMatches.index(True)
	except ValueError:
		defaultIndex = -1
		_moduleLogger.warn(
			"Could not find contact number %s among %r" % (
				default, numbers
			)
		)
	return defaultIndex


def _get_contact_numbers(session, contactId, number, description):
	contactPhoneNumbers = []
	if contactId and contactId != "0":
		try:
			contactDetails = copy.deepcopy(session.get_contacts()[contactId])
			contactPhoneNumbers = contactDetails["numbers"]
		except KeyError:
			contactPhoneNumbers = []
		contactPhoneNumbers = [
			(contactPhoneNumber["phoneNumber"], contactPhoneNumber.get("phoneType", "Unknown"))
			for contactPhoneNumber in contactPhoneNumbers
		]
		defaultIndex = _index_number(contactPhoneNumbers, number)

	if not contactPhoneNumbers or defaultIndex == -1:
		contactPhoneNumbers += [(number, description)]
		defaultIndex = 0

	return contactPhoneNumbers, defaultIndex
