#!/usr/bin/python2.5

# DialCentral - Front end for Google's Grand Central service.
# Copyright (C) 2008  Mark Bergman bergman AT merctech DOT com
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import threading
import time
import warnings

import gobject
import gtk

try:
	import hildon
except ImportError:
	hildon = None


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


def make_idler(func):
	"""
	Decorator that makes a generator-function into a function that will continue execution on next call
	"""
	a = []

	def decorated_func(*args, **kwds):
		if not a:
			a.append(func(*args, **kwds))
		try:
			a[0].next()
			return True
		except StopIteration:
			del a[:]
			return False

	decorated_func.__name__ = func.__name__
	decorated_func.__doc__ = func.__doc__
	decorated_func.__dict__.update(func.__dict__)

	return decorated_func


class DummyAddressBook(object):
	"""
	Minimal example of both an addressbook factory and an addressbook
	"""

	def clear_caches(self):
		pass

	def get_addressbooks(self):
		"""
		@returns Iterable of (Address Book Factory, Book Id, Book Name)
		"""
		yield self, "", "None"

	def open_addressbook(self, bookId):
		return self

	@staticmethod
	def contact_source_short_name(contactId):
		return ""

	@staticmethod
	def factory_name():
		return ""

	@staticmethod
	def get_contacts():
		"""
		@returns Iterable of (contact id, contact name)
		"""
		return []

	@staticmethod
	def get_contact_details(contactId):
		"""
		@returns Iterable of (Phone Type, Phone Number)
		"""
		return []


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
	def advanced_firtname_sorter(cls, contacts):
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

	def __init__(self, widgetTree, gcBackend):
		self._gcBackend = gcBackend
		self._widgetTree = widgetTree
		self._dialog = self._widgetTree.get_widget("phonetype_dialog")

		self._selectButton = self._widgetTree.get_widget("select_button")
		self._selectButton.connect("clicked", self._on_phonetype_select)

		self._cancelButton = self._widgetTree.get_widget("cancel_button")
		self._cancelButton.connect("clicked", self._on_phonetype_cancel)

		self._typemodel = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
		self._typeviewselection = None

		typeview = self._widgetTree.get_widget("phonetypes")
		typeview.connect("row-activated", self._on_phonetype_select)
		typeview.set_model(self._typemodel)
		textrenderer = gtk.CellRendererText()

		# Add the column to the treeview
		column = gtk.TreeViewColumn("Phone Numbers", textrenderer, text=1)
		column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)

		typeview.append_column(column)

		self._typeviewselection = typeview.get_selection()
		self._typeviewselection.set_mode(gtk.SELECTION_SINGLE)

	def run(self, contactDetails):
		self._typemodel.clear()

		for phoneType, phoneNumber in contactDetails:
			self._typemodel.append((phoneNumber, "%s - %s" % (make_pretty(phoneNumber), phoneType)))

		userResponse = self._dialog.run()

		if userResponse == gtk.RESPONSE_OK:
			model, itr = self._typeviewselection.get_selected()
			if itr:
				phoneNumber = self._typemodel.get_value(itr, 0)
		else:
			phoneNumber = ""

		self._typeviewselection.unselect_all()
		self._dialog.hide()
		return phoneNumber

	def _on_phonetype_select(self, *args):
		self._dialog.response(gtk.RESPONSE_OK)

	def _on_phonetype_cancel(self, *args):
		self._dialog.response(gtk.RESPONSE_CANCEL)


class Dialpad(object):

	def __init__(self, widgetTree):
		self._numberdisplay = widgetTree.get_widget("numberdisplay")
		self._phonenumber = ""
		self._prettynumber = ""
		self._clearall_id = None

		callbackMapping = {
			"on_dial_clicked": self._on_dial_clicked,
			"on_digit_clicked": self._on_digit_clicked,
			"on_clear_number": self._on_clear_number,
			"on_back_clicked": self._on_backspace,
			"on_back_pressed": self._on_back_pressed,
			"on_back_released": self._on_back_released,
		}
		widgetTree.signal_autoconnect(callbackMapping)
		widgetTree.get_widget("dial").grab_default()
		widgetTree.get_widget("dial").grab_focus()

	def enable(self):
		pass

	def disable(self):
		pass

	def dial(self, number):
		raise NotImplementedError

	def get_number(self):
		return self._phonenumber

	def set_number(self, number):
		"""
		Set the callback phonenumber
		"""
		self._phonenumber = make_ugly(number)
		self._prettynumber = make_pretty(self._phonenumber)
		self._numberdisplay.set_label("<span size='30000' weight='bold'>%s</span>" % (self._prettynumber))

	def clear(self):
		self.set_number("")

	def _on_dial_clicked(self, widget):
		self.dial(self.get_number())

	def _on_clear_number(self, *args):
		self.clear()

	def _on_digit_clicked(self, widget):
		self.set_number(self._phonenumber + widget.get_name()[-1])

	def _on_backspace(self, widget):
		self.set_number(self._phonenumber[:-1])

	def _on_clearall(self):
		self.clear()
		return False

	def _on_back_pressed(self, widget):
		self._clearall_id = gobject.timeout_add(1000, self._on_clearall)

	def _on_back_released(self, widget):
		if self._clearall_id is not None:
			gobject.source_remove(self._clearall_id)
		self._clearall_id = None


class AccountInfo(object):

	def __init__(self, widgetTree, backend = None):
		self._backend = backend

		self._callbackList = gtk.ListStore(gobject.TYPE_STRING)
		self._accountViewNumberDisplay = widgetTree.get_widget("gcnumber_display")
		self._callbackCombo = widgetTree.get_widget("callbackcombo")
		if hildon is not None:
			self._callbackCombo.get_child().set_property('hildon-input-mode', (1 << 4))

		callbackMapping = {
		}
		widgetTree.signal_autoconnect(callbackMapping)
		self._callbackCombo.get_child().connect("changed", self._on_callbackentry_changed)

		self.set_account_number("")

	def enable(self):
		pass

	def disable(self):
		pass

	def get_selected_callback_number(self):
		return make_ugly(self._callbackCombo.get_child().get_text())

	def set_account_number(self, number):
		"""
		Displays current account number
		"""
		self._accountViewNumberDisplay.set_label("<span size='23000' weight='bold'>%s</span>" % (number))

	def update(self):
		self.populate_callback_combo()
		self.set_account_number(self._backend.get_account_number())

	def clear(self):
		self._callbackCombo.get_child().set_text("")
		self.set_account_number("")

	def populate_callback_combo(self):
		self._callbackList.clear()
		for number, description in self._backend.get_callback_numbers().iteritems():
			self._callbackList.append((make_pretty(number),))

		self._callbackCombo.set_model(self._callbackList)
		self._callbackCombo.set_text_column(0)
		self._callbackCombo.get_child().set_text(make_pretty(self._backend.get_callback_number()))

	def _on_callbackentry_changed(self, *args):
		"""
		@todo Potential blocking on web access, maybe we should defer this or put up a dialog?
		"""
		text = self.get_selected_callback_number()
		if not self._backend.is_valid_syntax(text):
			warnings.warn("%s is not a valid callback number" % text, UserWarning, 2)
		elif text == self._backend.get_callback_number():
			warnings.warn("Callback number already is %s" % self._backend.get_callback_number(), UserWarning, 2)
		else:
			self._backend.set_callback_number(text)


class RecentCallsView(object):

	def __init__(self, widgetTree, backend = None):
		self._backend = backend
		self._recenttime = 0.0
		self._recentmodel = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
		self._recentview = widgetTree.get_widget("recentview")
		self._recentviewselection = None

		callbackMapping = {
			"on_recentview_row_activated": self._on_recentview_row_activated,
		}
		widgetTree.signal_autoconnect(callbackMapping)

		self._init_recent_view()
		if hildon is not None:
			hildon.hildon_helper_set_thumb_scrollbar(widgetTree.get_widget('recent_scrolledwindow'), True)

	def enable(self):
		pass

	def disable(self):
		pass

	def number_selected(self, number):
		raise NotImplementedError

	def update(self):
		if (time.time() - self._recenttime) < 300:
			return
		backgroundPopulate = threading.Thread(target=self._idly_populate_recentview)
		backgroundPopulate.setDaemon(True)
		backgroundPopulate.start()

	def clear(self):
		self._recenttime = 0.0
		self._recentmodel.clear()

	def _init_recent_view(self):
		self._recentview.set_model(self._recentmodel)
		textrenderer = gtk.CellRendererText()

		# Add the column to the treeview
		column = gtk.TreeViewColumn("Calls", textrenderer, text=1)
		column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)

		self._recentview.append_column(column)

		self._recentviewselection = self._recentview.get_selection()
		self._recentviewselection.set_mode(gtk.SELECTION_SINGLE)

	def _idly_populate_recentview(self):
		self._recenttime = time.time()
		self._recentmodel.clear()

		for personsName, phoneNumber, date, action in self._backend.get_recent():
			description = "%s on %s from/to %s - %s" % (action.capitalize(), date, personsName, phoneNumber)
			item = (phoneNumber, description)
			gtk.gdk.threads_enter()
			try:
				self._recentmodel.append(item)
			finally:
				gtk.gdk.threads_leave()

		return False

	def _on_recentview_row_activated(self, treeview, path, view_column):
		model, itr = self._recentviewselection.get_selected()
		if not itr:
			return

		self.number_selected(self._recentmodel.get_value(itr, 0))
		self._recentviewselection.unselect_all()


class ContactsView(object):

	def __init__(self, widgetTree, backend = None):
		self._backend = backend

		self._addressBook = None
		self._addressBookFactories = [DummyAddressBook()]

		self._booksList = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
		self._booksSelectionBox = widgetTree.get_widget("addressbook_combo")

		self._contactstime = 0.0
		self._contactsmodel = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
		self._contactsviewselection = None
		self._contactsview = widgetTree.get_widget("contactsview")

		self._phoneTypeSelector = PhoneTypeSelector(widgetTree, self._backend)

		callbackMapping = {
			"on_contactsview_row_activated" : self._on_contactsview_row_activated,
			"on_addressbook_combo_changed": self._on_addressbook_combo_changed,
		}
		widgetTree.signal_autoconnect(callbackMapping)
		if hildon is not None:
			hildon.hildon_helper_set_thumb_scrollbar(widgetTree.get_widget('contacts_scrolledwindow'), True)

		self._init_contacts_view()

	def enable(self):
		pass

	def disable(self):
		pass

	def number_selected(self, number):
		raise NotImplementedError

	def get_addressbooks(self):
		"""
		@returns Iterable of ((Factory Id, Book Id), (Factory Name, Book Name))
		"""
		for i, factory in enumerate(self._addressBookFactories):
			for bookFactory, bookId, bookName in factory.get_addressbooks():
				yield (i, bookId), (factory.factory_name(), bookName)

	def open_addressbook(self, bookFactoryId, bookId):
		self._addressBook = self._addressBookFactories[bookFactoryId].open_addressbook(bookId)
		self._contactstime = 0
		backgroundPopulate = threading.Thread(target=self._idly_populate_contactsview)
		backgroundPopulate.setDaemon(True)
		backgroundPopulate.start()

	def update(self):
		if (time.time() - self._contactstime) < 300:
			return
		backgroundPopulate = threading.Thread(target=self._idly_populate_contactsview)
		backgroundPopulate.setDaemon(True)
		backgroundPopulate.start()

	def clear(self):
		self._contactstime = 0.0
		self._contactsmodel.clear()

	def clear_caches(self):
		for factory in self._addressBookFactories:
			factory.clear_caches()
		self._addressBook.clear_caches()

	def append(self, book):
		self._addressBookFactories.append(book)

	def extend(self, books):
		self._addressBookFactories.extend(books)

	def _init_contacts_view(self):
		self._contactsview.set_model(self._contactsmodel)

		# Add the column to the treeview
		column = gtk.TreeViewColumn("Contact")

		#displayContactSource = False
		displayContactSource = True
		if displayContactSource:
			textrenderer = gtk.CellRendererText()
			column.pack_start(textrenderer, expand=False)
			column.add_attribute(textrenderer, 'text', 0)

		textrenderer = gtk.CellRendererText()
		column.pack_start(textrenderer, expand=True)
		column.add_attribute(textrenderer, 'text', 1)

		textrenderer = gtk.CellRendererText()
		column.pack_start(textrenderer, expand=True)
		column.add_attribute(textrenderer, 'text', 4)

		column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
		column.set_sort_column_id(1)
		column.set_visible(True)
		self._contactsview.append_column(column)

		self._contactsviewselection = self._contactsview.get_selection()
		self._contactsviewselection.set_mode(gtk.SELECTION_SINGLE)

	def _init_books_combo(self):
		self._booksList.clear()
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

		self._booksSelectionBox.set_model(self._booksList)
		cell = gtk.CellRendererText()
		self._booksSelectionBox.pack_start(cell, True)
		self._booksSelectionBox.add_attribute(cell, 'text', 2)
		self._booksSelectionBox.set_active(0)

	def _idly_populate_contactsview(self):
		#@todo Add a lock so only one code path can be in here at a time
		self.clear()

		# completely disable updating the treeview while we populate the data
		self._contactsview.freeze_child_notify()
		self._contactsview.set_model(None)

		addressBook = self._addressBook
		for contactId, contactName in addressBook.get_contacts():
			contactType = (addressBook.contact_source_short_name(contactId),)
			self._contactsmodel.append(contactType + (contactName, "", contactId) + ("",))

		# restart the treeview data rendering
		self._contactsview.set_model(self._contactsmodel)
		self._contactsview.thaw_child_notify()
		return False

	def _on_addressbook_combo_changed(self, *args, **kwds):
		itr = self._booksSelectionBox.get_active_iter()
		if itr is None:
			return
		factoryId = int(self._booksList.get_value(itr, 0))
		bookId = self._booksList.get_value(itr, 1)
		self.open_addressbook(factoryId, bookId)

	def _on_contactsview_row_activated(self, treeview, path, view_column):
		model, itr = self._contactsviewselection.get_selected()
		if not itr:
			return

		contactId = self._contactsmodel.get_value(itr, 3)
		contactDetails = self._addressBook.get_contact_details(contactId)
		contactDetails = [phoneNumber for phoneNumber in contactDetails]

		if len(contactDetails) == 0:
			phoneNumber = ""
		elif len(contactDetails) == 1:
			phoneNumber = contactDetails[0][1]
		else:
			phoneNumber = self._phoneTypeSelector.run(contactDetails)

		if 0 < len(phoneNumber):
			self.number_selected(phoneNumber)

		self._contactsviewselection.unselect_all()
