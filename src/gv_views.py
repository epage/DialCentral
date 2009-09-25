#!/usr/bin/python2.5

"""
DialCentral - Front end for Google's GoogleVoice service.
Copyright (C) 2008  Mark Bergman bergman AT merctech DOT com

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

@todo Alternate UI for dialogs (stackables)
"""

from __future__ import with_statement

import ConfigParser
import logging

import gobject
import pango
import gtk

import gtk_toolbox
import hildonize
import null_backend


def make_ugly(prettynumber):
	"""
	function to take a phone number and strip out all non-numeric
	characters

	>>> make_ugly("+012-(345)-678-90")
	'01234567890'
	"""
	import re
	uglynumber = re.sub('\D', '', prettynumber)
	return uglynumber


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
	'(234)-567-8901'
	>>> make_pretty("12345678901")
	'1 (234)-567-8901'
	>>> make_pretty("01234567890")
	'+012-(345)-678-90'
	"""
	if phonenumber is None or phonenumber is "":
		return ""

	phonenumber = make_ugly(phonenumber)

	if len(phonenumber) < 3:
		return phonenumber

	if phonenumber[0] == "0":
		prettynumber = ""
		prettynumber += "+%s" % phonenumber[0:3]
		if 3 < len(phonenumber):
			prettynumber += "-(%s)" % phonenumber[3:6]
			if 6 < len(phonenumber):
				prettynumber += "-%s" % phonenumber[6:9]
				if 9 < len(phonenumber):
					prettynumber += "-%s" % phonenumber[9:]
		return prettynumber
	elif len(phonenumber) <= 7:
		prettynumber = "%s-%s" % (phonenumber[0:3], phonenumber[3:])
	elif len(phonenumber) > 8 and phonenumber[0] == "1":
		prettynumber = "1 (%s)-%s-%s" % (phonenumber[1:4], phonenumber[4:7], phonenumber[7:])
	elif len(phonenumber) > 7:
		prettynumber = "(%s)-%s-%s" % (phonenumber[0:3], phonenumber[3:6], phonenumber[6:])
	return prettynumber


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


class MergedAddressBook(object):
	"""
	Merger of all addressbooks
	"""

	def __init__(self, addressbookFactories, sorter = None):
		self.__addressbookFactories = addressbookFactories
		self.__addressbooks = None
		self.__sort_contacts = sorter if sorter is not None else self.null_sorter

	def clear_caches(self):
		self.__addressbooks = None
		for factory in self.__addressbookFactories:
			factory.clear_caches()

	def get_addressbooks(self):
		"""
		@returns Iterable of (Address Book Factory, Book Id, Book Name)
		"""
		yield self, "", ""

	def open_addressbook(self, bookId):
		return self

	def contact_source_short_name(self, contactId):
		if self.__addressbooks is None:
			return ""
		bookIndex, originalId = contactId.split("-", 1)
		return self.__addressbooks[int(bookIndex)].contact_source_short_name(originalId)

	@staticmethod
	def factory_name():
		return "All Contacts"

	def get_contacts(self):
		"""
		@returns Iterable of (contact id, contact name)
		"""
		if self.__addressbooks is None:
			self.__addressbooks = list(
				factory.open_addressbook(id)
				for factory in self.__addressbookFactories
				for (f, id, name) in factory.get_addressbooks()
			)
		contacts = (
			("-".join([str(bookIndex), contactId]), contactName)
				for (bookIndex, addressbook) in enumerate(self.__addressbooks)
					for (contactId, contactName) in addressbook.get_contacts()
		)
		sortedContacts = self.__sort_contacts(contacts)
		return sortedContacts

	def get_contact_details(self, contactId):
		"""
		@returns Iterable of (Phone Type, Phone Number)
		"""
		if self.__addressbooks is None:
			return []
		bookIndex, originalId = contactId.split("-", 1)
		return self.__addressbooks[int(bookIndex)].get_contact_details(originalId)

	@staticmethod
	def null_sorter(contacts):
		"""
		Good for speed/low memory
		"""
		return contacts

	@staticmethod
	def basic_firtname_sorter(contacts):
		"""
		Expects names in "First Last" format
		"""
		contactsWithKey = [
			(contactName.rsplit(" ", 1)[0], (contactId, contactName))
				for (contactId, contactName) in contacts
		]
		contactsWithKey.sort()
		return (contactData for (lastName, contactData) in contactsWithKey)

	@staticmethod
	def basic_lastname_sorter(contacts):
		"""
		Expects names in "First Last" format
		"""
		contactsWithKey = [
			(contactName.rsplit(" ", 1)[-1], (contactId, contactName))
				for (contactId, contactName) in contacts
		]
		contactsWithKey.sort()
		return (contactData for (lastName, contactData) in contactsWithKey)

	@staticmethod
	def reversed_firtname_sorter(contacts):
		"""
		Expects names in "Last, First" format
		"""
		contactsWithKey = [
			(contactName.split(", ", 1)[-1], (contactId, contactName))
				for (contactId, contactName) in contacts
		]
		contactsWithKey.sort()
		return (contactData for (lastName, contactData) in contactsWithKey)

	@staticmethod
	def reversed_lastname_sorter(contacts):
		"""
		Expects names in "Last, First" format
		"""
		contactsWithKey = [
			(contactName.split(", ", 1)[0], (contactId, contactName))
				for (contactId, contactName) in contacts
		]
		contactsWithKey.sort()
		return (contactData for (lastName, contactData) in contactsWithKey)

	@staticmethod
	def guess_firstname(name):
		if ", " in name:
			return name.split(", ", 1)[-1]
		else:
			return name.rsplit(" ", 1)[0]

	@staticmethod
	def guess_lastname(name):
		if ", " in name:
			return name.split(", ", 1)[0]
		else:
			return name.rsplit(" ", 1)[-1]

	@classmethod
	def advanced_firstname_sorter(cls, contacts):
		contactsWithKey = [
			(cls.guess_firstname(contactName), (contactId, contactName))
				for (contactId, contactName) in contacts
		]
		contactsWithKey.sort()
		return (contactData for (lastName, contactData) in contactsWithKey)

	@classmethod
	def advanced_lastname_sorter(cls, contacts):
		contactsWithKey = [
			(cls.guess_lastname(contactName), (contactId, contactName))
				for (contactId, contactName) in contacts
		]
		contactsWithKey.sort()
		return (contactData for (lastName, contactData) in contactsWithKey)


class PhoneTypeSelector(object):

	ACTION_CANCEL = "cancel"
	ACTION_SELECT = "select"
	ACTION_DIAL = "dial"
	ACTION_SEND_SMS = "sms"

	def __init__(self, widgetTree, gcBackend):
		self._gcBackend = gcBackend
		self._widgetTree = widgetTree

		self._dialog = self._widgetTree.get_widget("phonetype_dialog")
		self._smsDialog = SmsEntryDialog(self._widgetTree)

		self._smsButton = self._widgetTree.get_widget("sms_button")
		self._smsButton.connect("clicked", self._on_phonetype_send_sms)

		self._dialButton = self._widgetTree.get_widget("dial_button")
		self._dialButton.connect("clicked", self._on_phonetype_dial)

		self._selectButton = self._widgetTree.get_widget("select_button")
		self._selectButton.connect("clicked", self._on_phonetype_select)

		self._cancelButton = self._widgetTree.get_widget("cancel_button")
		self._cancelButton.connect("clicked", self._on_phonetype_cancel)

		self._messagemodel = gtk.ListStore(gobject.TYPE_STRING)
		self._messagesView = self._widgetTree.get_widget("phoneSelectionMessages")
		self._scrollWindow = self._messagesView.get_parent()

		self._typemodel = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
		self._typeviewselection = None
		self._typeview = self._widgetTree.get_widget("phonetypes")
		self._typeview.connect("row-activated", self._on_phonetype_select)

		self._action = self.ACTION_CANCEL

	def run(self, contactDetails, messages = (), parent = None):
		self._action = self.ACTION_CANCEL

		# Add the column to the phone selection tree view
		self._typemodel.clear()
		self._typeview.set_model(self._typemodel)

		textrenderer = gtk.CellRendererText()
		numberColumn = gtk.TreeViewColumn("Phone Numbers", textrenderer, text=0)
		self._typeview.append_column(numberColumn)

		textrenderer = gtk.CellRendererText()
		typeColumn = gtk.TreeViewColumn("Phone Type", textrenderer, text=1)
		self._typeview.append_column(typeColumn)

		for phoneType, phoneNumber in contactDetails:
			display = " - ".join((phoneNumber, phoneType))
			display = phoneType
			row = (phoneNumber, display)
			self._typemodel.append(row)

		self._typeviewselection = self._typeview.get_selection()
		self._typeviewselection.set_mode(gtk.SELECTION_SINGLE)
		self._typeviewselection.select_iter(self._typemodel.get_iter_first())

		# Add the column to the messages tree view
		self._messagemodel.clear()
		self._messagesView.set_model(self._messagemodel)

		textrenderer = gtk.CellRendererText()
		textrenderer.set_property("wrap-mode", pango.WRAP_WORD)
		textrenderer.set_property("wrap-width", 450)
		messageColumn = gtk.TreeViewColumn("")
		messageColumn.pack_start(textrenderer, expand=True)
		messageColumn.add_attribute(textrenderer, "markup", 0)
		messageColumn.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
		self._messagesView.append_column(messageColumn)
		self._messagesView.set_headers_visible(False)

		if messages:
			for message in messages:
				row = (message, )
				self._messagemodel.append(row)
			self._messagesView.show()
			self._scrollWindow.show()
			messagesSelection = self._messagesView.get_selection()
			messagesSelection.select_path((len(messages)-1, ))
		else:
			self._messagesView.hide()
			self._scrollWindow.hide()

		if parent is not None:
			self._dialog.set_transient_for(parent)

		try:
			self._dialog.show()
			if messages:
				self._messagesView.scroll_to_cell((len(messages)-1, ))

			userResponse = self._dialog.run()
		finally:
			self._dialog.hide()

		if userResponse == gtk.RESPONSE_OK:
			phoneNumber = self._get_number()
			phoneNumber = make_ugly(phoneNumber)
		else:
			phoneNumber = ""
		if not phoneNumber:
			self._action = self.ACTION_CANCEL

		if self._action == self.ACTION_SEND_SMS:
			smsMessage = self._smsDialog.run(phoneNumber, messages, parent)
			if not smsMessage:
				phoneNumber = ""
				self._action = self.ACTION_CANCEL
		else:
			smsMessage = ""

		self._messagesView.remove_column(messageColumn)
		self._messagesView.set_model(None)

		self._typeviewselection.unselect_all()
		self._typeview.remove_column(numberColumn)
		self._typeview.remove_column(typeColumn)
		self._typeview.set_model(None)

		return self._action, phoneNumber, smsMessage

	def _get_number(self):
		model, itr = self._typeviewselection.get_selected()
		if not itr:
			return ""

		phoneNumber = self._typemodel.get_value(itr, 0)
		return phoneNumber

	def _on_phonetype_dial(self, *args):
		self._dialog.response(gtk.RESPONSE_OK)
		self._action = self.ACTION_DIAL

	def _on_phonetype_send_sms(self, *args):
		self._dialog.response(gtk.RESPONSE_OK)
		self._action = self.ACTION_SEND_SMS

	def _on_phonetype_select(self, *args):
		self._dialog.response(gtk.RESPONSE_OK)
		self._action = self.ACTION_SELECT

	def _on_phonetype_cancel(self, *args):
		self._dialog.response(gtk.RESPONSE_CANCEL)
		self._action = self.ACTION_CANCEL


class SmsEntryDialog(object):
	"""
	@todo Add multi-SMS messages like GoogleVoice
	"""

	MAX_CHAR = 160

	def __init__(self, widgetTree):
		self._widgetTree = widgetTree
		self._dialog = self._widgetTree.get_widget("smsDialog")

		self._smsButton = self._widgetTree.get_widget("sendSmsButton")
		self._smsButton.connect("clicked", self._on_send)

		self._cancelButton = self._widgetTree.get_widget("cancelSmsButton")
		self._cancelButton.connect("clicked", self._on_cancel)

		self._letterCountLabel = self._widgetTree.get_widget("smsLetterCount")

		self._messagemodel = gtk.ListStore(gobject.TYPE_STRING)
		self._messagesView = self._widgetTree.get_widget("smsMessages")
		self._scrollWindow = self._messagesView.get_parent()

		self._smsEntry = self._widgetTree.get_widget("smsEntry")
		self._smsEntry.get_buffer().connect("changed", self._on_entry_changed)

	def run(self, number, messages = (), parent = None):
		# Add the column to the messages tree view
		self._messagemodel.clear()
		self._messagesView.set_model(self._messagemodel)

		textrenderer = gtk.CellRendererText()
		textrenderer.set_property("wrap-mode", pango.WRAP_WORD)
		textrenderer.set_property("wrap-width", 450)
		messageColumn = gtk.TreeViewColumn("")
		messageColumn.pack_start(textrenderer, expand=True)
		messageColumn.add_attribute(textrenderer, "markup", 0)
		messageColumn.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
		self._messagesView.append_column(messageColumn)
		self._messagesView.set_headers_visible(False)

		if messages:
			for message in messages:
				row = (message, )
				self._messagemodel.append(row)
			self._messagesView.show()
			self._scrollWindow.show()
			messagesSelection = self._messagesView.get_selection()
			messagesSelection.select_path((len(messages)-1, ))
		else:
			self._messagesView.hide()
			self._scrollWindow.hide()

		self._smsEntry.get_buffer().set_text("")
		self._update_letter_count()

		if parent is not None:
			self._dialog.set_transient_for(parent)

		try:
			self._dialog.show()
			if messages:
				self._messagesView.scroll_to_cell((len(messages)-1, ))
			self._smsEntry.grab_focus()

			userResponse = self._dialog.run()
		finally:
			self._dialog.hide()

		if userResponse == gtk.RESPONSE_OK:
			entryBuffer = self._smsEntry.get_buffer()
			enteredMessage = entryBuffer.get_text(entryBuffer.get_start_iter(), entryBuffer.get_end_iter())
			enteredMessage = enteredMessage[0:self.MAX_CHAR]
		else:
			enteredMessage = ""

		self._messagesView.remove_column(messageColumn)
		self._messagesView.set_model(None)

		return enteredMessage.strip()

	def _update_letter_count(self, *args):
		entryLength = self._smsEntry.get_buffer().get_char_count()
		charsLeft = self.MAX_CHAR - entryLength
		self._letterCountLabel.set_text(str(charsLeft))
		if charsLeft < 0:
			self._smsButton.set_sensitive(False)
		else:
			self._smsButton.set_sensitive(True)

	def _on_entry_changed(self, *args):
		self._update_letter_count()

	def _on_send(self, *args):
		self._dialog.response(gtk.RESPONSE_OK)

	def _on_cancel(self, *args):
		self._dialog.response(gtk.RESPONSE_CANCEL)


class Dialpad(object):

	def __init__(self, widgetTree, errorDisplay):
		self._clipboard = gtk.clipboard_get()
		self._errorDisplay = errorDisplay
		self._smsDialog = SmsEntryDialog(widgetTree)

		self._numberdisplay = widgetTree.get_widget("numberdisplay")
		self._smsButton = widgetTree.get_widget("sms")
		self._dialButton = widgetTree.get_widget("dial")
		self._backButton = widgetTree.get_widget("back")
		self._phonenumber = ""
		self._prettynumber = ""

		callbackMapping = {
			"on_digit_clicked": self._on_digit_clicked,
		}
		widgetTree.signal_autoconnect(callbackMapping)
		self._dialButton.connect("clicked", self._on_dial_clicked)
		self._smsButton.connect("clicked", self._on_sms_clicked)

		self._originalLabel = self._backButton.get_label()
		self._backTapHandler = gtk_toolbox.TapOrHold(self._backButton)
		self._backTapHandler.on_tap = self._on_backspace
		self._backTapHandler.on_hold = self._on_clearall
		self._backTapHandler.on_holding = self._set_clear_button
		self._backTapHandler.on_cancel = self._reset_back_button

		self._window = gtk_toolbox.find_parent_window(self._numberdisplay)
		self._keyPressEventId = 0

	def enable(self):
		self._dialButton.grab_focus()
		self._backTapHandler.enable()
		self._keyPressEventId = self._window.connect("key-press-event", self._on_key_press)

	def disable(self):
		self._window.disconnect(self._keyPressEventId)
		self._keyPressEventId = 0
		self._reset_back_button()
		self._backTapHandler.disable()

	def number_selected(self, action, number, message):
		"""
		@note Actual dial function is patched in later
		"""
		raise NotImplementedError("Horrible unknown error has occurred")

	def get_number(self):
		return self._phonenumber

	def set_number(self, number):
		"""
		Set the number to dial
		"""
		try:
			self._phonenumber = make_ugly(number)
			self._prettynumber = make_pretty(self._phonenumber)
			self._numberdisplay.set_label("<span size='30000' weight='bold'>%s</span>" % (self._prettynumber))
		except TypeError, e:
			self._errorDisplay.push_exception()

	def clear(self):
		self.set_number("")

	@staticmethod
	def name():
		return "Dialpad"

	def load_settings(self, config, section):
		pass

	def save_settings(self, config, section):
		"""
		@note Thread Agnostic
		"""
		pass

	def _on_key_press(self, widget, event):
		try:
			if event.keyval == ord("v") and event.get_state() & gtk.gdk.CONTROL_MASK:
				contents = self._clipboard.wait_for_text()
				if contents is not None:
					self.set_number(contents)
		except Exception, e:
			self._errorDisplay.push_exception()

	def _on_sms_clicked(self, widget):
		try:
			action = PhoneTypeSelector.ACTION_SEND_SMS
			phoneNumber = self.get_number()

			message = self._smsDialog.run(phoneNumber, (), self._window)
			if not message:
				phoneNumber = ""
				action = PhoneTypeSelector.ACTION_CANCEL

			if action == PhoneTypeSelector.ACTION_CANCEL:
				return
			self.number_selected(action, phoneNumber, message)
		except Exception, e:
			self._errorDisplay.push_exception()

	def _on_dial_clicked(self, widget):
		try:
			action = PhoneTypeSelector.ACTION_DIAL
			phoneNumber = self.get_number()
			message = ""
			self.number_selected(action, phoneNumber, message)
		except Exception, e:
			self._errorDisplay.push_exception()

	def _on_digit_clicked(self, widget):
		try:
			self.set_number(self._phonenumber + widget.get_name()[-1])
		except Exception, e:
			self._errorDisplay.push_exception()

	def _on_backspace(self, taps):
		try:
			self.set_number(self._phonenumber[:-taps])
			self._reset_back_button()
		except Exception, e:
			self._errorDisplay.push_exception()

	def _on_clearall(self, taps):
		try:
			self.clear()
			self._reset_back_button()
		except Exception, e:
			self._errorDisplay.push_exception()
		return False

	def _set_clear_button(self):
		try:
			self._backButton.set_label("gtk-clear")
		except Exception, e:
			self._errorDisplay.push_exception()

	def _reset_back_button(self):
		try:
			self._backButton.set_label(self._originalLabel)
		except Exception, e:
			self._errorDisplay.push_exception()


class AccountInfo(object):

	def __init__(self, widgetTree, backend, alarmHandler, errorDisplay):
		self._errorDisplay = errorDisplay
		self._backend = backend
		self._isPopulated = False
		self._alarmHandler = alarmHandler
		self._notifyOnMissed = False
		self._notifyOnVoicemail = False
		self._notifyOnSms = False

		self._callbackList = []
		self._accountViewNumberDisplay = widgetTree.get_widget("gcnumber_display")
		self._callbackSelectButton = widgetTree.get_widget("callbackSelectButton")
		self._onCallbackSelectChangedId = 0

		self._notifyCheckbox = widgetTree.get_widget("notifyCheckbox")
		self._minutesEntryButton = widgetTree.get_widget("minutesEntryButton")
		self._missedCheckbox = widgetTree.get_widget("missedCheckbox")
		self._voicemailCheckbox = widgetTree.get_widget("voicemailCheckbox")
		self._smsCheckbox = widgetTree.get_widget("smsCheckbox")
		self._onNotifyToggled = 0
		self._onMinutesChanged = 0
		self._onMissedToggled = 0
		self._onVoicemailToggled = 0
		self._onSmsToggled = 0
		self._applyAlarmTimeoutId = None

		self._window = gtk_toolbox.find_parent_window(self._minutesEntryButton)
		self._defaultCallback = ""

	def enable(self):
		assert self._backend.is_authed(), "Attempting to enable backend while not logged in"

		self._accountViewNumberDisplay.set_use_markup(True)
		self.set_account_number("")

		del self._callbackList[:]
		self._onCallbackSelectChangedId = self._callbackSelectButton.connect("clicked", self._on_callbackentry_clicked)

		if self._alarmHandler is not None:
			self._notifyCheckbox.set_active(self._alarmHandler.isEnabled)
			self._minutesEntryButton.set_label("%d minutes" % self._alarmHandler.recurrence)
			self._missedCheckbox.set_active(self._notifyOnMissed)
			self._voicemailCheckbox.set_active(self._notifyOnVoicemail)
			self._smsCheckbox.set_active(self._notifyOnSms)

			self._onNotifyToggled = self._notifyCheckbox.connect("toggled", self._on_notify_toggled)
			self._onMinutesChanged = self._minutesEntryButton.connect("clicked", self._on_minutes_clicked)
			self._onMissedToggled = self._missedCheckbox.connect("toggled", self._on_missed_toggled)
			self._onVoicemailToggled = self._voicemailCheckbox.connect("toggled", self._on_voicemail_toggled)
			self._onSmsToggled = self._smsCheckbox.connect("toggled", self._on_sms_toggled)
		else:
			self._notifyCheckbox.set_sensitive(False)
			self._minutesEntryButton.set_sensitive(False)
			self._missedCheckbox.set_sensitive(False)
			self._voicemailCheckbox.set_sensitive(False)
			self._smsCheckbox.set_sensitive(False)

		self.update(force=True)

	def disable(self):
		self._callbackSelectButton.disconnect(self._onCallbackSelectChangedId)
		self._onCallbackSelectChangedId = 0

		if self._alarmHandler is not None:
			self._notifyCheckbox.disconnect(self._onNotifyToggled)
			self._minutesEntryButton.disconnect(self._onMinutesChanged)
			self._missedCheckbox.disconnect(self._onNotifyToggled)
			self._voicemailCheckbox.disconnect(self._onNotifyToggled)
			self._smsCheckbox.disconnect(self._onNotifyToggled)
			self._onNotifyToggled = 0
			self._onMinutesChanged = 0
			self._onMissedToggled = 0
			self._onVoicemailToggled = 0
			self._onSmsToggled = 0
		else:
			self._notifyCheckbox.set_sensitive(True)
			self._minutesEntryButton.set_sensitive(True)
			self._missedCheckbox.set_sensitive(True)
			self._voicemailCheckbox.set_sensitive(True)
			self._smsCheckbox.set_sensitive(True)

		self.clear()
		del self._callbackList[:]

	def get_selected_callback_number(self):
		currentLabel = self._callbackSelectButton.get_label()
		if currentLabel is not None:
			return make_ugly(currentLabel)
		else:
			return ""

	def set_account_number(self, number):
		"""
		Displays current account number
		"""
		self._accountViewNumberDisplay.set_label("<span size='23000' weight='bold'>%s</span>" % (number))

	def update(self, force = False):
		if not force and self._isPopulated:
			return False
		self._populate_callback_combo()
		self.set_account_number(self._backend.get_account_number())
		return True

	def clear(self):
		self._callbackSelectButton.set_label("")
		self.set_account_number("")
		self._isPopulated = False

	def save_everything(self):
		raise NotImplementedError

	@staticmethod
	def name():
		return "Account Info"

	def load_settings(self, config, section):
		self._defaultCallback = config.get(section, "callback")
		self._notifyOnMissed = config.getboolean(section, "notifyOnMissed")
		self._notifyOnVoicemail = config.getboolean(section, "notifyOnVoicemail")
		self._notifyOnSms = config.getboolean(section, "notifyOnSms")

	def save_settings(self, config, section):
		"""
		@note Thread Agnostic
		"""
		callback = self.get_selected_callback_number()
		config.set(section, "callback", callback)
		config.set(section, "notifyOnMissed", repr(self._notifyOnMissed))
		config.set(section, "notifyOnVoicemail", repr(self._notifyOnVoicemail))
		config.set(section, "notifyOnSms", repr(self._notifyOnSms))

	def _populate_callback_combo(self):
		self._isPopulated = True
		del self._callbackList[:]
		try:
			callbackNumbers = self._backend.get_callback_numbers()
		except Exception, e:
			self._errorDisplay.push_exception()
			self._isPopulated = False
			return

		for number, description in callbackNumbers.iteritems():
			self._callbackList.append(make_pretty(number))

		if not self.get_selected_callback_number():
			self._set_callback_number(self._defaultCallback)

	def _set_callback_number(self, number):
		try:
			if not self._backend.is_valid_syntax(number) and 0 < len(number):
				self._errorDisplay.push_message("%s is not a valid callback number" % number)
			elif number == self._backend.get_callback_number():
				logging.warning(
					"Callback number already is %s" % (
						self._backend.get_callback_number(),
					),
				)
			else:
				self._backend.set_callback_number(number)
				assert make_ugly(number) == make_ugly(self._backend.get_callback_number()), "Callback number should be %s but instead is %s" % (
					make_pretty(number), make_pretty(self._backend.get_callback_number())
				)
				self._callbackSelectButton.set_label(make_pretty(number))
				logging.info(
					"Callback number set to %s" % (
						self._backend.get_callback_number(),
					),
				)
		except Exception, e:
			self._errorDisplay.push_exception()

	def _update_alarm_settings(self, recurrence):
		try:
			isEnabled = self._notifyCheckbox.get_active()
			if isEnabled != self._alarmHandler.isEnabled or recurrence != self._alarmHandler.recurrence:
				self._alarmHandler.apply_settings(isEnabled, recurrence)
		finally:
			self.save_everything()
			self._notifyCheckbox.set_active(self._alarmHandler.isEnabled)
			self._minutesEntryButton.set_label("%d Minutes" % self._alarmHandler.recurrence)

	def _on_callbackentry_clicked(self, *args):
		try:
			actualSelection = make_pretty(self.get_selected_callback_number())

			userSelection = hildonize.touch_selector_entry(
				self._window,
				"Callback Number",
				self._callbackList,
				actualSelection,
			)
			number = make_ugly(userSelection)
			self._set_callback_number(number)
		except RuntimeError, e:
			logging.exception("%s" % str(e))
		except Exception, e:
			self._errorDisplay.push_exception()

	def _on_notify_toggled(self, *args):
		try:
			if self._applyAlarmTimeoutId is not None:
				gobject.source_remove(self._applyAlarmTimeoutId)
				self._applyAlarmTimeoutId = None
			self._applyAlarmTimeoutId = gobject.timeout_add(500, self._on_apply_timeout)
		except Exception, e:
			self._errorDisplay.push_exception()

	def _on_minutes_clicked(self, *args):
		recurrenceChoices = [
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
		try:
			actualSelection = self._alarmHandler.recurrence

			closestSelectionIndex = 0
			for i, possible in enumerate(recurrenceChoices):
				if possible[0] <= actualSelection:
					closestSelectionIndex = i
			recurrenceIndex = hildonize.touch_selector(
				self._window,
				"Minutes",
				(("%s" % m[1]) for m in recurrenceChoices),
				closestSelectionIndex,
			)
			recurrence = recurrenceChoices[recurrenceIndex][0]

			self._update_alarm_settings(recurrence)
		except RuntimeError, e:
			logging.exception("%s" % str(e))
		except Exception, e:
			self._errorDisplay.push_exception()

	def _on_apply_timeout(self, *args):
		try:
			self._applyAlarmTimeoutId = None

			self._update_alarm_settings(self._alarmHandler.recurrence)
		except Exception, e:
			self._errorDisplay.push_exception()
		return False

	def _on_missed_toggled(self, *args):
		try:
			self._notifyOnMissed = self._missedCheckbox.get_active()
			self.save_everything()
		except Exception, e:
			self._errorDisplay.push_exception()

	def _on_voicemail_toggled(self, *args):
		try:
			self._notifyOnVoicemail = self._voicemailCheckbox.get_active()
			self.save_everything()
		except Exception, e:
			self._errorDisplay.push_exception()

	def _on_sms_toggled(self, *args):
		try:
			self._notifyOnSms = self._smsCheckbox.get_active()
			self.save_everything()
		except Exception, e:
			self._errorDisplay.push_exception()


class RecentCallsView(object):

	NUMBER_IDX = 0
	DATE_IDX = 1
	ACTION_IDX = 2
	FROM_IDX = 3

	def __init__(self, widgetTree, backend, errorDisplay):
		self._errorDisplay = errorDisplay
		self._backend = backend

		self._isPopulated = False
		self._recentmodel = gtk.ListStore(
			gobject.TYPE_STRING, # number
			gobject.TYPE_STRING, # date
			gobject.TYPE_STRING, # action
			gobject.TYPE_STRING, # from
		)
		self._recentview = widgetTree.get_widget("recentview")
		self._recentviewselection = None
		self._onRecentviewRowActivatedId = 0

		textrenderer = gtk.CellRendererText()
		textrenderer.set_property("yalign", 0)
		self._dateColumn = gtk.TreeViewColumn("Date")
		self._dateColumn.pack_start(textrenderer, expand=True)
		self._dateColumn.add_attribute(textrenderer, "text", self.DATE_IDX)

		textrenderer = gtk.CellRendererText()
		textrenderer.set_property("yalign", 0)
		self._actionColumn = gtk.TreeViewColumn("Action")
		self._actionColumn.pack_start(textrenderer, expand=True)
		self._actionColumn.add_attribute(textrenderer, "text", self.ACTION_IDX)

		textrenderer = gtk.CellRendererText()
		textrenderer.set_property("yalign", 0)
		textrenderer.set_property("ellipsize", pango.ELLIPSIZE_END)
		textrenderer.set_property("width-chars", len("1 (555) 555-1234"))
		self._numberColumn = gtk.TreeViewColumn("Number")
		self._numberColumn.pack_start(textrenderer, expand=True)
		self._numberColumn.add_attribute(textrenderer, "text", self.NUMBER_IDX)

		textrenderer = gtk.CellRendererText()
		textrenderer.set_property("yalign", 0)
		hildonize.set_cell_thumb_selectable(textrenderer)
		self._nameColumn = gtk.TreeViewColumn("From")
		self._nameColumn.pack_start(textrenderer, expand=True)
		self._nameColumn.add_attribute(textrenderer, "text", self.FROM_IDX)
		self._nameColumn.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)

		self._window = gtk_toolbox.find_parent_window(self._recentview)
		self._phoneTypeSelector = PhoneTypeSelector(widgetTree, self._backend)

		self._updateSink = gtk_toolbox.threaded_stage(
			gtk_toolbox.comap(
				self._idly_populate_recentview,
				gtk_toolbox.null_sink(),
			)
		)

	def enable(self):
		assert self._backend.is_authed(), "Attempting to enable backend while not logged in"
		self._recentview.set_model(self._recentmodel)

		self._recentview.append_column(self._dateColumn)
		self._recentview.append_column(self._actionColumn)
		self._recentview.append_column(self._numberColumn)
		self._recentview.append_column(self._nameColumn)
		self._recentviewselection = self._recentview.get_selection()
		self._recentviewselection.set_mode(gtk.SELECTION_SINGLE)

		self._onRecentviewRowActivatedId = self._recentview.connect("row-activated", self._on_recentview_row_activated)

	def disable(self):
		self._recentview.disconnect(self._onRecentviewRowActivatedId)

		self.clear()

		self._recentview.remove_column(self._dateColumn)
		self._recentview.remove_column(self._actionColumn)
		self._recentview.remove_column(self._nameColumn)
		self._recentview.remove_column(self._numberColumn)
		self._recentview.set_model(None)

	def number_selected(self, action, number, message):
		"""
		@note Actual dial function is patched in later
		"""
		raise NotImplementedError("Horrible unknown error has occurred")

	def update(self, force = False):
		if not force and self._isPopulated:
			return False
		self._updateSink.send(())
		return True

	def clear(self):
		self._isPopulated = False
		self._recentmodel.clear()

	@staticmethod
	def name():
		return "Recent Calls"

	def load_settings(self, config, section):
		pass

	def save_settings(self, config, section):
		"""
		@note Thread Agnostic
		"""
		pass

	def _idly_populate_recentview(self):
		with gtk_toolbox.gtk_lock():
			banner = hildonize.show_busy_banner_start(self._window, "Loading Recent History")
		try:
			self._recentmodel.clear()
			self._isPopulated = True

			try:
				recentItems = self._backend.get_recent()
			except Exception, e:
				self._errorDisplay.push_exception_with_lock()
				self._isPopulated = False
				recentItems = []

			for personName, phoneNumber, date, action in recentItems:
				if not personName:
					personName = "Unknown"
				date = abbrev_relative_date(date)
				prettyNumber = phoneNumber[2:] if phoneNumber.startswith("+1") else phoneNumber
				prettyNumber = make_pretty(prettyNumber)
				item = (prettyNumber, date, action.capitalize(), personName)
				with gtk_toolbox.gtk_lock():
					self._recentmodel.append(item)
		except Exception, e:
			self._errorDisplay.push_exception_with_lock()
		finally:
			with gtk_toolbox.gtk_lock():
				hildonize.show_busy_banner_end(banner)

		return False

	def _on_recentview_row_activated(self, treeview, path, view_column):
		try:
			model, itr = self._recentviewselection.get_selected()
			if not itr:
				return

			number = self._recentmodel.get_value(itr, self.NUMBER_IDX)
			number = make_ugly(number)
			contactPhoneNumbers = [("Phone", number)]
			description = self._recentmodel.get_value(itr, self.FROM_IDX)

			action, phoneNumber, message = self._phoneTypeSelector.run(
				contactPhoneNumbers,
				messages = (description, ),
				parent = self._window,
			)
			if action == PhoneTypeSelector.ACTION_CANCEL:
				return
			assert phoneNumber, "A lack of phone number exists"

			self.number_selected(action, phoneNumber, message)
			self._recentviewselection.unselect_all()
		except Exception, e:
			self._errorDisplay.push_exception()


class MessagesView(object):

	NUMBER_IDX = 0
	DATE_IDX = 1
	HEADER_IDX = 2
	MESSAGE_IDX = 3
	MESSAGES_IDX = 4

	def __init__(self, widgetTree, backend, errorDisplay):
		self._errorDisplay = errorDisplay
		self._backend = backend

		self._isPopulated = False
		self._messagemodel = gtk.ListStore(
			gobject.TYPE_STRING, # number
			gobject.TYPE_STRING, # date
			gobject.TYPE_STRING, # header
			gobject.TYPE_STRING, # message
			object, # messages
		)
		self._messageview = widgetTree.get_widget("messages_view")
		self._messageviewselection = None
		self._onMessageviewRowActivatedId = 0

		self._messageRenderer = gtk.CellRendererText()
		self._messageRenderer.set_property("wrap-mode", pango.WRAP_WORD)
		self._messageRenderer.set_property("wrap-width", 500)
		self._messageColumn = gtk.TreeViewColumn("Messages")
		self._messageColumn.pack_start(self._messageRenderer, expand=True)
		self._messageColumn.add_attribute(self._messageRenderer, "markup", self.MESSAGE_IDX)
		self._messageColumn.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)

		self._window = gtk_toolbox.find_parent_window(self._messageview)
		self._phoneTypeSelector = PhoneTypeSelector(widgetTree, self._backend)

		self._updateSink = gtk_toolbox.threaded_stage(
			gtk_toolbox.comap(
				self._idly_populate_messageview,
				gtk_toolbox.null_sink(),
			)
		)

	def enable(self):
		assert self._backend.is_authed(), "Attempting to enable backend while not logged in"
		self._messageview.set_model(self._messagemodel)
		self._messageview.set_headers_visible(False)

		self._messageview.append_column(self._messageColumn)
		self._messageviewselection = self._messageview.get_selection()
		self._messageviewselection.set_mode(gtk.SELECTION_SINGLE)

		self._onMessageviewRowActivatedId = self._messageview.connect("row-activated", self._on_messageview_row_activated)

	def disable(self):
		self._messageview.disconnect(self._onMessageviewRowActivatedId)

		self.clear()

		self._messageview.remove_column(self._messageColumn)
		self._messageview.set_model(None)

	def number_selected(self, action, number, message):
		"""
		@note Actual dial function is patched in later
		"""
		raise NotImplementedError("Horrible unknown error has occurred")

	def update(self, force = False):
		if not force and self._isPopulated:
			return False
		self._updateSink.send(())
		return True

	def clear(self):
		self._isPopulated = False
		self._messagemodel.clear()

	@staticmethod
	def name():
		return "Messages"

	def load_settings(self, config, section):
		pass

	def save_settings(self, config, section):
		"""
		@note Thread Agnostic
		"""
		pass

	def _idly_populate_messageview(self):
		with gtk_toolbox.gtk_lock():
			banner = hildonize.show_busy_banner_start(self._window, "Loading Messages")
		try:
			self._messagemodel.clear()
			self._isPopulated = True

			try:
				messageItems = self._backend.get_messages()
			except Exception, e:
				self._errorDisplay.push_exception_with_lock()
				self._isPopulated = False
				messageItems = []

			for header, number, relativeDate, messages in messageItems:
				prettyNumber = number[2:] if number.startswith("+1") else number
				prettyNumber = make_pretty(prettyNumber)

				firstMessage = "<b>%s - %s</b> <i>(%s)</i>" % (header, prettyNumber, relativeDate)
				newMessages = [firstMessage]
				newMessages.extend(messages)

				number = make_ugly(number)

				row = (number, relativeDate, header, "\n".join(newMessages), newMessages)
				with gtk_toolbox.gtk_lock():
					self._messagemodel.append(row)
		except Exception, e:
			self._errorDisplay.push_exception_with_lock()
		finally:
			with gtk_toolbox.gtk_lock():
				hildonize.show_busy_banner_end(banner)

		return False

	def _on_messageview_row_activated(self, treeview, path, view_column):
		try:
			model, itr = self._messageviewselection.get_selected()
			if not itr:
				return

			contactPhoneNumbers = [("Phone", self._messagemodel.get_value(itr, self.NUMBER_IDX))]
			description = self._messagemodel.get_value(itr, self.MESSAGES_IDX)

			action, phoneNumber, message = self._phoneTypeSelector.run(
				contactPhoneNumbers,
				messages = description,
				parent = self._window,
			)
			if action == PhoneTypeSelector.ACTION_CANCEL:
				return
			assert phoneNumber, "A lock of phone number exists"

			self.number_selected(action, phoneNumber, message)
			self._messageviewselection.unselect_all()
		except Exception, e:
			self._errorDisplay.push_exception()


class ContactsView(object):

	def __init__(self, widgetTree, backend, errorDisplay):
		self._errorDisplay = errorDisplay
		self._backend = backend

		self._addressBook = None
		self._selectedComboIndex = 0
		self._addressBookFactories = [null_backend.NullAddressBook()]

		self._booksList = []
		self._bookSelectionButton = widgetTree.get_widget("addressbookSelectButton")

		self._isPopulated = False
		self._contactsmodel = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
		self._contactsviewselection = None
		self._contactsview = widgetTree.get_widget("contactsview")

		self._contactColumn = gtk.TreeViewColumn("Contact")
		displayContactSource = False
		if displayContactSource:
			textrenderer = gtk.CellRendererText()
			self._contactColumn.pack_start(textrenderer, expand=False)
			self._contactColumn.add_attribute(textrenderer, 'text', 0)
		textrenderer = gtk.CellRendererText()
		hildonize.set_cell_thumb_selectable(textrenderer)
		self._contactColumn.pack_start(textrenderer, expand=True)
		self._contactColumn.add_attribute(textrenderer, 'text', 1)
		textrenderer = gtk.CellRendererText()
		self._contactColumn.pack_start(textrenderer, expand=True)
		self._contactColumn.add_attribute(textrenderer, 'text', 4)
		self._contactColumn.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
		self._contactColumn.set_sort_column_id(1)
		self._contactColumn.set_visible(True)

		self._onContactsviewRowActivatedId = 0
		self._onAddressbookButtonChangedId = 0
		self._window = gtk_toolbox.find_parent_window(self._contactsview)
		self._phoneTypeSelector = PhoneTypeSelector(widgetTree, self._backend)

		self._updateSink = gtk_toolbox.threaded_stage(
			gtk_toolbox.comap(
				self._idly_populate_contactsview,
				gtk_toolbox.null_sink(),
			)
		)

	def enable(self):
		assert self._backend.is_authed(), "Attempting to enable backend while not logged in"

		self._contactsview.set_model(self._contactsmodel)
		self._contactsview.append_column(self._contactColumn)
		self._contactsviewselection = self._contactsview.get_selection()
		self._contactsviewselection.set_mode(gtk.SELECTION_SINGLE)

		del self._booksList[:]
		for (factoryId, bookId), (factoryName, bookName) in self.get_addressbooks():
			if factoryName and bookName:
				entryName = "%s: %s" % (factoryName, bookName)
			elif factoryName:
				entryName = factoryName
			elif bookName:
				entryName = bookName
			else:
				entryName = "Bad name (%d)" % factoryId
			row = (str(factoryId), bookId, entryName)
			self._booksList.append(row)

		self._onContactsviewRowActivatedId = self._contactsview.connect("row-activated", self._on_contactsview_row_activated)
		self._onAddressbookButtonChangedId = self._bookSelectionButton.connect("clicked", self._on_addressbook_button_changed)

		if len(self._booksList) <= self._selectedComboIndex:
			self._selectedComboIndex = 0
		self._bookSelectionButton.set_label(self._booksList[self._selectedComboIndex][2])

		selectedFactoryId = self._booksList[self._selectedComboIndex][0]
		selectedBookId = self._booksList[self._selectedComboIndex][1]
		self.open_addressbook(selectedFactoryId, selectedBookId)

	def disable(self):
		self._contactsview.disconnect(self._onContactsviewRowActivatedId)
		self._bookSelectionButton.disconnect(self._onAddressbookButtonChangedId)

		self.clear()

		self._bookSelectionButton.set_label("")
		self._contactsview.set_model(None)
		self._contactsview.remove_column(self._contactColumn)

	def number_selected(self, action, number, message):
		"""
		@note Actual dial function is patched in later
		"""
		raise NotImplementedError("Horrible unknown error has occurred")

	def get_addressbooks(self):
		"""
		@returns Iterable of ((Factory Id, Book Id), (Factory Name, Book Name))
		"""
		for i, factory in enumerate(self._addressBookFactories):
			for bookFactory, bookId, bookName in factory.get_addressbooks():
				yield (str(i), bookId), (factory.factory_name(), bookName)

	def open_addressbook(self, bookFactoryId, bookId):
		bookFactoryIndex = int(bookFactoryId)
		addressBook = self._addressBookFactories[bookFactoryIndex].open_addressbook(bookId)

		forceUpdate = True if addressBook is not self._addressBook else False

		self._addressBook = addressBook
		self.update(force=forceUpdate)

	def update(self, force = False):
		if not force and self._isPopulated:
			return False
		self._updateSink.send(())
		return True

	def clear(self):
		self._isPopulated = False
		self._contactsmodel.clear()
		for factory in self._addressBookFactories:
			factory.clear_caches()
		self._addressBook.clear_caches()

	def append(self, book):
		self._addressBookFactories.append(book)

	def extend(self, books):
		self._addressBookFactories.extend(books)

	@staticmethod
	def name():
		return "Contacts"

	def load_settings(self, config, sectionName):
		try:
			self._selectedComboIndex = config.getint(sectionName, "selectedAddressbook")
		except ConfigParser.NoOptionError:
			self._selectedComboIndex = 0

	def save_settings(self, config, sectionName):
		config.set(sectionName, "selectedAddressbook", str(self._selectedComboIndex))

	def _idly_populate_contactsview(self):
		with gtk_toolbox.gtk_lock():
			banner = hildonize.show_busy_banner_start(self._window, "Loading Contacts")
		try:
			addressBook = None
			while addressBook is not self._addressBook:
				addressBook = self._addressBook
				with gtk_toolbox.gtk_lock():
					self._contactsview.set_model(None)
					self.clear()

				try:
					contacts = addressBook.get_contacts()
				except Exception, e:
					contacts = []
					self._isPopulated = False
					self._errorDisplay.push_exception_with_lock()
				for contactId, contactName in contacts:
					contactType = (addressBook.contact_source_short_name(contactId), )
					self._contactsmodel.append(contactType + (contactName, "", contactId) + ("", ))

				with gtk_toolbox.gtk_lock():
					self._contactsview.set_model(self._contactsmodel)

			self._isPopulated = True
		except Exception, e:
			self._errorDisplay.push_exception_with_lock()
		finally:
			with gtk_toolbox.gtk_lock():
				hildonize.show_busy_banner_end(banner)
		return False

	def _on_addressbook_button_changed(self, *args, **kwds):
		try:
			try:
				newSelectedComboIndex = hildonize.touch_selector(
					self._window,
					"Addressbook",
					(("%s" % m[2]) for m in self._booksList),
					self._selectedComboIndex,
				)
			except RuntimeError:
				return

			selectedFactoryId = self._booksList[newSelectedComboIndex][0]
			selectedBookId = self._booksList[newSelectedComboIndex][1]
			self.open_addressbook(selectedFactoryId, selectedBookId)
			self._selectedComboIndex = newSelectedComboIndex
			self._bookSelectionButton.set_label(self._booksList[self._selectedComboIndex][2])
		except Exception, e:
			self._errorDisplay.push_exception()

	def _on_contactsview_row_activated(self, treeview, path, view_column):
		try:
			model, itr = self._contactsviewselection.get_selected()
			if not itr:
				return

			contactId = self._contactsmodel.get_value(itr, 3)
			contactName = self._contactsmodel.get_value(itr, 1)
			try:
				contactDetails = self._addressBook.get_contact_details(contactId)
			except Exception, e:
				contactDetails = []
				self._errorDisplay.push_exception()
			contactPhoneNumbers = [phoneNumber for phoneNumber in contactDetails]

			if len(contactPhoneNumbers) == 0:
				return

			action, phoneNumber, message = self._phoneTypeSelector.run(
				contactPhoneNumbers,
				messages = (contactName, ),
				parent = self._window,
			)
			if action == PhoneTypeSelector.ACTION_CANCEL:
				return
			assert phoneNumber, "A lack of phone number exists"

			self.number_selected(action, phoneNumber, message)
			self._contactsviewselection.unselect_all()
		except Exception, e:
			self._errorDisplay.push_exception()
