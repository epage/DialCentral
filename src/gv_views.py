#!/usr/bin/env python

from __future__ import with_statement
from __future__ import division

import logging

from PyQt4 import QtGui
from PyQt4 import QtCore

from util import qtpie
from util import qui_utils
from util import misc as misc_utils

import backends.null_backend as null_backend
import backends.file_backend as file_backend


_moduleLogger = logging.getLogger(__name__)


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

	def get_settings(self):
		return {}

	def set_settings(self, settings):
		pass

	def clear(self):
		pass

	def refresh(self, force = True):
		pass

	def _generate_key_button(self, center, letters):
		centerPieItem = self._generate_button_slice(center)
		pieItems = [
			pieItem
			for pieItem in self._generate_button_slices(letters)
		]

		button = qtpie.QPieButton(centerPieItem)
		button.set_center(centerPieItem)
		for item in pieItems:
			button.insertItem(item)

		return button

	def _generate_button_slices(self, letters):
		if len(letters) == 0:
			for i in xrange(8):
				pieItem = qtpie.PieFiling.NULL_CENTER
				yield pieItem
		elif len(letters) in [3, 4]:
			for i in xrange(6 - len(letters)):
				pieItem = qtpie.PieFiling.NULL_CENTER
				yield pieItem

			for letter in letters:
				pieItem = self._generate_button_slice(letter)
				yield pieItem

			for i in xrange(2):
				pieItem = qtpie.PieFiling.NULL_CENTER
				yield pieItem
		else:
			raise NotImplementedError("Cannot handle %r" % letters)

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

	def get_settings(self):
		return {
			"filter": str(self._typeSelection.currentText()),
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
		self._session.update_history(force)

	def _populate_items(self):
		self._itemStore.clear()
		history = self._session.get_history()
		history.sort(key=lambda item: item["time"], reverse=True)
		for event in history:
			if self._selectedFilter in [self.HISTORY_ITEM_TYPES[-1], event["action"]]:
				relTime = misc_utils.abbrev_relative_date(event["relTime"])
				action = event["action"]
				number = event["number"]
				prettyNumber = misc_utils.make_pretty(number)
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
			relTime = misc_utils.abbrev_relative_date(iContactDetails[QtCore.QString("relTime")])
			action = str(iContactDetails[QtCore.QString("action")])
			number = str(iContactDetails[QtCore.QString("number")])
			prettyNumber = misc_utils.make_pretty(number)
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

	def get_settings(self):
		return {
			"type": str(self._typeSelection.currentText()),
			"status": str(self._statusSelection.currentText()),
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

	# @todo Provide some sort of letter jump

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

	def get_settings(self):
		return {
			"selectedAddressbook": str(self._listSelection.currentText()),
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
