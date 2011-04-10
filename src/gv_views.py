#!/usr/bin/env python

from __future__ import with_statement
from __future__ import division

import datetime
import string
import itertools
import logging

from PyQt4 import QtGui
from PyQt4 import QtCore

from util import qtpie
from util import qui_utils
from util import misc as misc_utils

import backends.null_backend as null_backend
import backends.file_backend as file_backend


_moduleLogger = logging.getLogger(__name__)


_SENTINEL_ICON = QtGui.QIcon()


class Dialpad(object):

	def __init__(self, app, session, errorLog):
		self._app = app
		self._session = session
		self._errorLog = errorLog

		self._plus = QtGui.QPushButton("+")
		self._plus.clicked.connect(lambda: self._on_keypress("+"))
		self._entry = QtGui.QLineEdit()

		backAction = QtGui.QAction(None)
		backAction.setText("Back")
		backAction.triggered.connect(self._on_backspace)
		backPieItem = qtpie.QActionPieItem(backAction)
		clearAction = QtGui.QAction(None)
		clearAction.setText("Clear")
		clearAction.triggered.connect(self._on_clear_text)
		clearPieItem = qtpie.QActionPieItem(clearAction)
		backSlices = [
			qtpie.PieFiling.NULL_CENTER,
			clearPieItem,
			qtpie.PieFiling.NULL_CENTER,
			qtpie.PieFiling.NULL_CENTER,
		]
		self._back = qtpie.QPieButton(backPieItem)
		self._back.set_center(backPieItem)
		for slice in backSlices:
			self._back.insertItem(slice)

		self._entryLayout = QtGui.QHBoxLayout()
		self._entryLayout.addWidget(self._plus, 1, QtCore.Qt.AlignCenter)
		self._entryLayout.addWidget(self._entry, 1000)
		self._entryLayout.addWidget(self._back, 1, QtCore.Qt.AlignCenter)

		smsIcon = self._app.get_icon("messages.png")
		self._smsButton = QtGui.QPushButton(smsIcon, "SMS")
		self._smsButton.clicked.connect(self._on_sms_clicked)
		self._smsButton.setSizePolicy(QtGui.QSizePolicy(
			QtGui.QSizePolicy.MinimumExpanding,
			QtGui.QSizePolicy.MinimumExpanding,
			QtGui.QSizePolicy.PushButton,
		))
		callIcon = self._app.get_icon("dialpad.png")
		self._callButton = QtGui.QPushButton(callIcon, "Call")
		self._callButton.clicked.connect(self._on_call_clicked)
		self._callButton.setSizePolicy(QtGui.QSizePolicy(
			QtGui.QSizePolicy.MinimumExpanding,
			QtGui.QSizePolicy.MinimumExpanding,
			QtGui.QSizePolicy.PushButton,
		))

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
			self._padLayout.addWidget(self._generate_key_button(num, letters), row, column)
		self._zerothButton = QtGui.QPushButton("0")
		self._zerothButton.clicked.connect(lambda: self._on_keypress("0"))
		self._zerothButton.setSizePolicy(QtGui.QSizePolicy(
			QtGui.QSizePolicy.MinimumExpanding,
			QtGui.QSizePolicy.MinimumExpanding,
			QtGui.QSizePolicy.PushButton,
		))
		self._padLayout.addWidget(self._smsButton, 3, 0)
		self._padLayout.addWidget(self._zerothButton)
		self._padLayout.addWidget(self._callButton, 3, 2)

		self._layout = QtGui.QVBoxLayout()
		self._layout.addLayout(self._entryLayout, 0)
		self._layout.addLayout(self._padLayout, 1000000)
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

	def get_settings(self):
		return {}

	def set_settings(self, settings):
		pass

	def clear(self):
		pass

	def refresh(self, force = True):
		pass

	def _generate_key_button(self, center, letters):
		button = QtGui.QPushButton("%s\n%s" % (center, letters))
		button.setSizePolicy(QtGui.QSizePolicy(
			QtGui.QSizePolicy.MinimumExpanding,
			QtGui.QSizePolicy.MinimumExpanding,
			QtGui.QSizePolicy.PushButton,
		))
		button.clicked.connect(lambda: self._on_keypress(center))
		return button

	@misc_utils.log_exception(_moduleLogger)
	def _on_keypress(self, key):
		with qui_utils.notify_error(self._errorLog):
			self._entry.insert(key)

	@misc_utils.log_exception(_moduleLogger)
	def _on_backspace(self, toggled = False):
		with qui_utils.notify_error(self._errorLog):
			self._entry.backspace()

	@misc_utils.log_exception(_moduleLogger)
	def _on_clear_text(self, toggled = False):
		with qui_utils.notify_error(self._errorLog):
			self._entry.clear()

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_sms_clicked(self, checked = False):
		with qui_utils.notify_error(self._errorLog):
			number = misc_utils.make_ugly(str(self._entry.text()))
			self._entry.clear()

			contactId = number
			title = misc_utils.make_pretty(number)
			description = misc_utils.make_pretty(number)
			numbersWithDescriptions = [(number, "")]
			self._session.draft.add_contact(contactId, None, title, description, numbersWithDescriptions)

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc_utils.log_exception(_moduleLogger)
	def _on_call_clicked(self, checked = False):
		with qui_utils.notify_error(self._errorLog):
			number = misc_utils.make_ugly(str(self._entry.text()))
			self._entry.clear()

			contactId = number
			title = misc_utils.make_pretty(number)
			description = misc_utils.make_pretty(number)
			numbersWithDescriptions = [(number, "")]
			self._session.draft.clear()
			self._session.draft.add_contact(contactId, None, title, description, numbersWithDescriptions)
			self._session.draft.call()


class TimeCategories(object):

	_NOW_SECTION = 0
	_TODAY_SECTION = 1
	_WEEK_SECTION = 2
	_MONTH_SECTION = 3
	_REST_SECTION = 4
	_MAX_SECTIONS = 5

	_NO_ELAPSED = datetime.timedelta(hours=1)
	_WEEK_ELAPSED = datetime.timedelta(weeks=1)
	_MONTH_ELAPSED = datetime.timedelta(days=30)

	def __init__(self, parentItem):
		self._timeItems = [
			QtGui.QStandardItem(description)
			for (i, description) in zip(
				xrange(self._MAX_SECTIONS),
				["Now", "Today", "Week", "Month", "Past"],
			)
		]
		for item in self._timeItems:
			item.setEditable(False)
			item.setCheckable(False)
			row = (item, )
			parentItem.appendRow(row)

		self._today = datetime.datetime(1900, 1, 1)

		self.prepare_for_update(self._today)

	def prepare_for_update(self, newToday):
		self._today = newToday
		for item in self._timeItems:
			item.removeRows(0, item.rowCount())
		try:
			hour = self._today.strftime("%X")
			day = self._today.strftime("%x")
		except ValueError:
			_moduleLogger.exception("Can't format times")
			hour = "Now"
			day = "Today"
		self._timeItems[self._NOW_SECTION].setText(hour)
		self._timeItems[self._TODAY_SECTION].setText(day)

	def add_row(self, rowDate, row):
		elapsedTime = self._today - rowDate
		todayTuple = self._today.timetuple()
		rowTuple = rowDate.timetuple()
		if elapsedTime < self._NO_ELAPSED:
			section = self._NOW_SECTION
		elif todayTuple[0:3] == rowTuple[0:3]:
			section = self._TODAY_SECTION
		elif elapsedTime < self._WEEK_ELAPSED:
			section = self._WEEK_SECTION
		elif elapsedTime < self._MONTH_ELAPSED:
			section = self._MONTH_SECTION
		else:
			section = self._REST_SECTION
		self._timeItems[section].appendRow(row)

	def get_item(self, timeIndex, rowIndex, column):
		timeItem = self._timeItems[timeIndex]
		item = timeItem.child(rowIndex, column)
		return item


class History(object):

	DETAILS_IDX = 0
	FROM_IDX = 1
	MAX_IDX = 2

	HISTORY_RECEIVED = "Received"
	HISTORY_MISSED = "Missed"
	HISTORY_PLACED = "Placed"
	HISTORY_ALL = "All"

	HISTORY_ITEM_TYPES = [HISTORY_RECEIVED, HISTORY_MISSED, HISTORY_PLACED, HISTORY_ALL]
	HISTORY_COLUMNS = ["Details", "From"]
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
		refreshIcon = qui_utils.get_theme_icon(
			("view-refresh", "general_refresh", "gtk-refresh", ),
			_SENTINEL_ICON
		)
		if refreshIcon is not _SENTINEL_ICON:
			self._refreshButton = QtGui.QPushButton(refreshIcon, "")
		else:
			self._refreshButton = QtGui.QPushButton("Refresh")
		self._refreshButton.clicked.connect(self._on_refresh_clicked)
		self._refreshButton.setSizePolicy(QtGui.QSizePolicy(
			QtGui.QSizePolicy.Minimum,
			QtGui.QSizePolicy.Minimum,
			QtGui.QSizePolicy.PushButton,
		))
		self._managerLayout = QtGui.QHBoxLayout()
		self._managerLayout.addWidget(self._typeSelection, 1000)
		self._managerLayout.addWidget(self._refreshButton, 0)

		self._itemStore = QtGui.QStandardItemModel()
		self._itemStore.setHorizontalHeaderLabels(self.HISTORY_COLUMNS)
		self._categoryManager = TimeCategories(self._itemStore)

		self._itemView = QtGui.QTreeView()
		self._itemView.setModel(self._itemStore)
		self._itemView.setUniformRowHeights(True)
		self._itemView.setRootIsDecorated(False)
		self._itemView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self._itemView.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
		self._itemView.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
		self._itemView.setHeaderHidden(True)
		self._itemView.setItemsExpandable(False)
		self._itemView.header().setResizeMode(QtGui.QHeaderView.ResizeToContents)
		self._itemView.activated.connect(self._on_row_activated)

		self._layout = QtGui.QVBoxLayout()
		self._layout.addLayout(self._managerLayout)
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

	def get_settings(self):
		return {
			"filter": self._selectedFilter,
		}

	def set_settings(self, settings):
		selectedFilter = settings.get("filter", self.HISTORY_ITEM_TYPES[-1])
		if selectedFilter in self.HISTORY_ITEM_TYPES:
			self._selectedFilter = selectedFilter
			self._typeSelection.setCurrentIndex(
				self.HISTORY_ITEM_TYPES.index(selectedFilter)
			)

	def clear(self):
		self._itemView.clear()

	def refresh(self, force=True):
		self._itemView.setFocus(QtCore.Qt.OtherFocusReason)

		if self._selectedFilter == self.HISTORY_RECEIVED:
			self._session.update_history(self._session.HISTORY_RECEIVED, force)
		elif self._selectedFilter == self.HISTORY_MISSED:
			self._session.update_history(self._session.HISTORY_MISSED, force)
		elif self._selectedFilter == self.HISTORY_PLACED:
			self._session.update_history(self._session.HISTORY_PLACED, force)
		elif self._selectedFilter == self.HISTORY_ALL:
			self._session.update_history(self._session.HISTORY_ALL, force)
		else:
			assert False, "How did we get here?"

		if self._app.notifyOnMissed and self._app.alarmHandler.alarmType == self._app.alarmHandler.ALARM_BACKGROUND:
			self._app.ledHandler.off()

	def _populate_items(self):
		self._categoryManager.prepare_for_update(self._session.get_when_history_updated())

		history = self._session.get_history()
		history.sort(key=lambda item: item["time"], reverse=True)
		for event in history:
			if self._selectedFilter not in [self.HISTORY_ITEM_TYPES[-1], event["action"]]:
				continue

			relTime = misc_utils.abbrev_relative_date(event["relTime"])
			action = event["action"]
			number = event["number"]
			prettyNumber = misc_utils.make_pretty(number)
			name = event["name"]
			if not name or name == number:
				name = event["location"]
			if not name:
				name = "Unknown"

			detailsItem = QtGui.QStandardItem("%s - %s\n%s" % (relTime, action, prettyNumber))
			detailsFont = detailsItem.font()
			detailsFont.setPointSize(max(detailsFont.pointSize() - 7, 5))
			detailsItem.setFont(detailsFont)
			nameItem = QtGui.QStandardItem(name)
			nameFont = nameItem.font()
			nameFont.setPointSize(nameFont.pointSize() + 4)
			nameItem.setFont(nameFont)
			row = detailsItem, nameItem
			for item in row:
				item.setEditable(False)
				item.setCheckable(False)
			row[0].setData(event)
			self._categoryManager.add_row(event["time"], row)
		self._itemView.expandAll()

	@QtCore.pyqtSlot(str)
	@misc_utils.log_exception(_moduleLogger)
	def _on_filter_changed(self, newItem):
		with qui_utils.notify_error(self._errorLog):
			self._selectedFilter = str(newItem)
			self._populate_items()

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_history_updated(self):
		with qui_utils.notify_error(self._errorLog):
			self._populate_items()

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_refresh_clicked(self, arg = None):
		with qui_utils.notify_error(self._errorLog):
			self.refresh(force=True)

	@QtCore.pyqtSlot(QtCore.QModelIndex)
	@misc_utils.log_exception(_moduleLogger)
	def _on_row_activated(self, index):
		with qui_utils.notify_error(self._errorLog):
			timeIndex = index.parent()
			if not timeIndex.isValid():
				return
			timeRow = timeIndex.row()
			row = index.row()
			detailsItem = self._categoryManager.get_item(timeRow, row, self.DETAILS_IDX)
			fromItem = self._categoryManager.get_item(timeRow, row, self.FROM_IDX)
			contactDetails = detailsItem.data().toPyObject()

			title = unicode(fromItem.text())
			number = str(contactDetails[QtCore.QString("number")])
			contactId = number # ids don't seem too unique so using numbers

			descriptionRows = []
			for t in xrange(self._itemStore.rowCount()):
				randomTimeItem = self._itemStore.item(t, 0)
				for i in xrange(randomTimeItem.rowCount()):
					iItem = randomTimeItem.child(i, 0)
					iContactDetails = iItem.data().toPyObject()
					iNumber = str(iContactDetails[QtCore.QString("number")])
					if number != iNumber:
						continue
					relTime = misc_utils.abbrev_relative_date(iContactDetails[QtCore.QString("relTime")])
					action = str(iContactDetails[QtCore.QString("action")])
					number = str(iContactDetails[QtCore.QString("number")])
					prettyNumber = misc_utils.make_pretty(number)
					rowItems = relTime, action, prettyNumber
					descriptionRows.append("<tr><td>%s</td></tr>" % "</td><td>".join(rowItems))
			description = "<table>%s</table>" % "".join(descriptionRows)
			numbersWithDescriptions = [(str(contactDetails[QtCore.QString("number")]), "")]
			self._session.draft.add_contact(contactId, None, title, description, numbersWithDescriptions)


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

	_MIN_MESSAGES_SHOWN = 1

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

		refreshIcon = qui_utils.get_theme_icon(
			("view-refresh", "general_refresh", "gtk-refresh", ),
			_SENTINEL_ICON
		)
		if refreshIcon is not _SENTINEL_ICON:
			self._refreshButton = QtGui.QPushButton(refreshIcon, "")
		else:
			self._refreshButton = QtGui.QPushButton("Refresh")
		self._refreshButton.clicked.connect(self._on_refresh_clicked)
		self._refreshButton.setSizePolicy(QtGui.QSizePolicy(
			QtGui.QSizePolicy.Minimum,
			QtGui.QSizePolicy.Minimum,
			QtGui.QSizePolicy.PushButton,
		))

		self._selectionLayout = QtGui.QHBoxLayout()
		self._selectionLayout.addWidget(self._typeSelection, 1000)
		self._selectionLayout.addWidget(self._statusSelection, 1000)
		self._selectionLayout.addWidget(self._refreshButton, 0)

		self._itemStore = QtGui.QStandardItemModel()
		self._itemStore.setHorizontalHeaderLabels(["Messages"])
		self._categoryManager = TimeCategories(self._itemStore)

		self._htmlDelegate = qui_utils.QHtmlDelegate()
		self._itemView = QtGui.QTreeView()
		self._itemView.setModel(self._itemStore)
		self._itemView.setUniformRowHeights(False)
		self._itemView.setRootIsDecorated(False)
		self._itemView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self._itemView.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
		self._itemView.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
		self._itemView.setHeaderHidden(True)
		self._itemView.setItemsExpandable(False)
		self._itemView.setItemDelegate(self._htmlDelegate)
		self._itemView.activated.connect(self._on_row_activated)
		self._itemView.header().sectionResized.connect(self._on_column_resized)

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

	def get_settings(self):
		return {
			"type": self._selectedTypeFilter,
			"status": self._selectedStatusFilter,
		}

	def set_settings(self, settings):
		selectedType = settings.get("type", self.ALL_TYPES)
		if selectedType in self.MESSAGE_TYPES:
			self._selectedTypeFilter = selectedType
			self._typeSelection.setCurrentIndex(
				self.MESSAGE_TYPES.index(self._selectedTypeFilter)
			)

		selectedStatus = settings.get("status", self.ALL_STATUS)
		if selectedStatus in self.MESSAGE_STATUSES:
			self._selectedStatusFilter = selectedStatus
			self._statusSelection.setCurrentIndex(
				self.MESSAGE_STATUSES.index(self._selectedStatusFilter)
			)

	def clear(self):
		self._itemView.clear()

	def refresh(self, force=True):
		self._itemView.setFocus(QtCore.Qt.OtherFocusReason)

		if self._selectedTypeFilter == self.NO_MESSAGES:
			pass
		elif self._selectedTypeFilter == self.TEXT_MESSAGES:
			self._session.update_messages(self._session.MESSAGE_TEXTS, force)
		elif self._selectedTypeFilter == self.VOICEMAIL_MESSAGES:
			self._session.update_messages(self._session.MESSAGE_VOICEMAILS, force)
		elif self._selectedTypeFilter == self.ALL_TYPES:
			self._session.update_messages(self._session.MESSAGE_ALL, force)
		else:
			assert False, "How did we get here?"

		if self._app.notifyOnSms or self._app.notifyOnVoicemail and self._app.alarmHandler.alarmType == self._app.alarmHandler.ALARM_BACKGROUND:
			self._app.ledHandler.off()

	def _populate_items(self):
		self._categoryManager.prepare_for_update(self._session.get_when_messages_updated())

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
			if not (visibleType and visibleStatus):
				continue

			relTime = misc_utils.abbrev_relative_date(item["relTime"])
			number = item["number"]
			prettyNumber = misc_utils.make_pretty(number)
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

			firstMessage = "<b>%s<br/>%s</b> <i>(%s)</i>" % (name, prettyNumber, relTime)

			expandedMessages = [firstMessage]
			expandedMessages.extend(messages)
			if self._MIN_MESSAGES_SHOWN < len(messages):
				secondMessage = "<i>%d Messages Hidden...</i>" % (len(messages) - self._MIN_MESSAGES_SHOWN, )
				collapsedMessages = [firstMessage, secondMessage]
				collapsedMessages.extend(messages[-(self._MIN_MESSAGES_SHOWN+0):])
			else:
				collapsedMessages = expandedMessages

			item = dict(item.iteritems())
			item["collapsedMessages"] = "<br/>\n".join(collapsedMessages)
			item["expandedMessages"] = "<br/>\n".join(expandedMessages)

			messageItem = QtGui.QStandardItem(item["collapsedMessages"])
			messageItem.setData(item)
			messageItem.setEditable(False)
			messageItem.setCheckable(False)
			row = (messageItem, )
			self._categoryManager.add_row(item["time"], row)
		self._itemView.expandAll()

	@QtCore.pyqtSlot(str)
	@misc_utils.log_exception(_moduleLogger)
	def _on_type_filter_changed(self, newItem):
		with qui_utils.notify_error(self._errorLog):
			self._selectedTypeFilter = str(newItem)
			self._populate_items()

	@QtCore.pyqtSlot(str)
	@misc_utils.log_exception(_moduleLogger)
	def _on_status_filter_changed(self, newItem):
		with qui_utils.notify_error(self._errorLog):
			self._selectedStatusFilter = str(newItem)
			self._populate_items()

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_refresh_clicked(self, arg = None):
		with qui_utils.notify_error(self._errorLog):
			self.refresh(force=True)

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_messages_updated(self):
		with qui_utils.notify_error(self._errorLog):
			self._populate_items()

	@QtCore.pyqtSlot(QtCore.QModelIndex)
	@misc_utils.log_exception(_moduleLogger)
	def _on_row_activated(self, index):
		with qui_utils.notify_error(self._errorLog):
			timeIndex = index.parent()
			if not timeIndex.isValid():
				return
			timeRow = timeIndex.row()
			row = index.row()
			item = self._categoryManager.get_item(timeRow, row, 0)
			contactDetails = item.data().toPyObject()

			name = unicode(contactDetails[QtCore.QString("name")])
			number = str(contactDetails[QtCore.QString("number")])
			if not name or name == number:
				name = unicode(contactDetails[QtCore.QString("location")])
			if not name:
				name = "Unknown"

			if str(contactDetails[QtCore.QString("type")]) == "Voicemail":
				messageId = str(contactDetails[QtCore.QString("id")])
			else:
				messageId = None
			contactId = str(contactDetails[QtCore.QString("contactId")])
			title = name
			description = unicode(contactDetails[QtCore.QString("expandedMessages")])
			numbersWithDescriptions = [(number, "")]
			self._session.draft.add_contact(contactId, messageId, title, description, numbersWithDescriptions)

	@QtCore.pyqtSlot(QtCore.QModelIndex)
	@misc_utils.log_exception(_moduleLogger)
	def _on_column_resized(self, index, oldSize, newSize):
		self._htmlDelegate.setWidth(newSize, self._itemStore)


class Contacts(object):

	# @todo Provide some sort of letter jump

	def __init__(self, app, session, errorLog):
		self._app = app
		self._session = session
		self._session.accountUpdated.connect(self._on_contacts_updated)
		self._errorLog = errorLog
		self._addressBookFactories = [
			null_backend.NullAddressBookFactory(),
			file_backend.FilesystemAddressBookFactory(app.fsContactsPath),
		]
		self._addressBooks = []

		self._listSelection = QtGui.QComboBox()
		self._listSelection.addItems([])
		self._listSelection.currentIndexChanged[str].connect(self._on_filter_changed)
		self._activeList = "None"
		refreshIcon = qui_utils.get_theme_icon(
			("view-refresh", "general_refresh", "gtk-refresh", ),
			_SENTINEL_ICON
		)
		if refreshIcon is not _SENTINEL_ICON:
			self._refreshButton = QtGui.QPushButton(refreshIcon, "")
		else:
			self._refreshButton = QtGui.QPushButton("Refresh")
		self._refreshButton.clicked.connect(self._on_refresh_clicked)
		self._refreshButton.setSizePolicy(QtGui.QSizePolicy(
			QtGui.QSizePolicy.Minimum,
			QtGui.QSizePolicy.Minimum,
			QtGui.QSizePolicy.PushButton,
		))
		self._managerLayout = QtGui.QHBoxLayout()
		self._managerLayout.addWidget(self._listSelection, 1000)
		self._managerLayout.addWidget(self._refreshButton, 0)

		self._itemStore = QtGui.QStandardItemModel()
		self._itemStore.setHorizontalHeaderLabels(["Contacts"])
		self._alphaItem = {}

		self._itemView = QtGui.QTreeView()
		self._itemView.setModel(self._itemStore)
		self._itemView.setUniformRowHeights(True)
		self._itemView.setRootIsDecorated(False)
		self._itemView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self._itemView.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
		self._itemView.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
		self._itemView.setHeaderHidden(True)
		self._itemView.setItemsExpandable(False)
		self._itemView.activated.connect(self._on_row_activated)

		self._layout = QtGui.QVBoxLayout()
		self._layout.addLayout(self._managerLayout)
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

	def get_settings(self):
		return {
			"selectedAddressbook": self._activeList,
		}

	def set_settings(self, settings):
		currentItem = settings.get("selectedAddressbook", "None")
		bookNames = [book["name"] for book in self._addressBooks]
		try:
			newIndex = bookNames.index(currentItem)
		except ValueError:
			# Switch over to None for the user
			newIndex = 0
		self._listSelection.setCurrentIndex(newIndex)
		self._activeList = currentItem

	def clear(self):
		self._itemView.clear()

	def refresh(self, force=True):
		self._itemView.setFocus(QtCore.Qt.OtherFocusReason)
		self._backend.update_account(force)

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
		self._activeList = currentItem
		if currentItem == "":
			# Not loaded yet
			currentItem = "None"
		self._listSelection.clear()
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
		self._alphaItem = dict(
			(letter, QtGui.QStandardItem(letter))
			for letter in self._prefixes()
		)
		for letter in self._prefixes():
			item = self._alphaItem[letter]
			item.setEditable(False)
			item.setCheckable(False)
			row = (item, )
			self._itemStore.appendRow(row)

		for item in self._get_contacts():
			name = item["name"]
			if not name:
				name = "Unknown"
			numbers = item["numbers"]

			nameItem = QtGui.QStandardItem(name)
			nameItem.setEditable(False)
			nameItem.setCheckable(False)
			nameItem.setData(item)
			nameItemFont = nameItem.font()
			nameItemFont.setPointSize(max(nameItemFont.pointSize() + 4, 5))
			nameItem.setFont(nameItemFont)

			row = (nameItem, )
			rowKey = name[0].upper()
			rowKey = rowKey if rowKey in self._alphaItem else "#"
			self._alphaItem[rowKey].appendRow(row)
		self._itemView.expandAll()

	def _prefixes(self):
		return itertools.chain(string.ascii_uppercase, ("#", ))

	def _jump_to_prefix(self, letter):
		i = list(self._prefixes()).index(letter)
		rootIndex = self._itemView.rootIndex()
		currentIndex = self._itemView.model().index(i, 0, rootIndex)
		self._itemView.scrollTo(currentIndex)
		self._itemView.setItemSelected(self._itemView.topLevelItem(i), True)

	def _get_contacts(self):
		contacts = list(self._backend.get_contacts().itervalues())
		contacts.sort(key=lambda contact: contact["name"].lower())
		return contacts

	@QtCore.pyqtSlot(str)
	@misc_utils.log_exception(_moduleLogger)
	def _on_filter_changed(self, newItem):
		with qui_utils.notify_error(self._errorLog):
			self._activeList = str(newItem)
			self.refresh(force=False)
			self._populate_items()

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_refresh_clicked(self, arg = None):
		with qui_utils.notify_error(self._errorLog):
			self.refresh(force=True)

	@QtCore.pyqtSlot()
	@misc_utils.log_exception(_moduleLogger)
	def _on_contacts_updated(self):
		with qui_utils.notify_error(self._errorLog):
			self._populate_items()

	@QtCore.pyqtSlot(QtCore.QModelIndex)
	@misc_utils.log_exception(_moduleLogger)
	def _on_row_activated(self, index):
		with qui_utils.notify_error(self._errorLog):
			letterIndex = index.parent()
			if not letterIndex.isValid():
				return
			letterRow = letterIndex.row()
			letter = list(self._prefixes())[letterRow]
			letterItem = self._alphaItem[letter]
			rowIndex = index.row()
			item = letterItem.child(rowIndex, 0)
			contactDetails = item.data().toPyObject()

			name = unicode(contactDetails[QtCore.QString("name")])
			if not name:
				name = unicode(contactDetails[QtCore.QString("location")])
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
			self._session.draft.add_contact(contactId, None, title, description, numbersWithDescriptions)

	@staticmethod
	def _choose_phonetype(numberDetails):
		if "phoneTypeName" in numberDetails:
			return numberDetails["phoneTypeName"]
		elif "phoneType" in numberDetails:
			return numberDetails["phoneType"]
		else:
			return ""
