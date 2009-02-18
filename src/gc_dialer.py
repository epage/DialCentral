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


"""
DialCentral: A phone dialer using GrandCentral
"""

import sys
import gc
import os
import threading
import time
import warnings

import gobject
import gtk
import gtk.glade

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

	def __init__(self, addressbooks, sorter = None):
		self.__addressbooks = addressbooks
		self.__sort_contacts = sorter if sorter is not None else self.null_sorter

	def clear_caches(self):
		for addressBook in self.__addressbooks:
			addressBook.clear_caches()

	def get_addressbooks(self):
		"""
		@returns Iterable of (Address Book Factory, Book Id, Book Name)
		"""
		yield self, "", ""

	def open_addressbook(self, bookId):
		return self

	def contact_source_short_name(self, contactId):
		bookIndex, originalId = contactId.split("-", 1)
		return self.__addressbooks[int(bookIndex)].contact_source_short_name(originalId)

	@staticmethod
	def factory_name():
		return "All Contacts"

	def get_contacts(self):
		"""
		@returns Iterable of (contact id, contact name)
		"""
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
		bookIndex, originalId = contactId.split("-", 1)
		return self.__addressbooks[int(bookIndex)].get_contact_details(originalId)

	@staticmethod
	def null_sorter(contacts):
		return contacts

	@staticmethod
	def basic_lastname_sorter(contacts):
		contactsWithKey = [
			(contactName.rsplit(" ", 1)[-1], (contactId, contactName))
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


class Dialcentral(object):

	__pretty_app_name__ = "DialCentral"
	__app_name__ = "dialcentral"
	__version__ = "0.8.4"
	__app_magic__ = 0xdeadbeef

	_glade_files = [
		'/usr/lib/dialcentral/dialcentral.glade',
		os.path.join(os.path.dirname(__file__), "dialcentral.glade"),
		os.path.join(os.path.dirname(__file__), "../lib/dialcentral.glade"),
	]

	def __init__(self):
		self._gcBackend = None
		self._clipboard = gtk.clipboard_get()

		self._deviceIsOnline = True
		self._dialpad = None
		self._accountView = None
		self._recentView = None
		self._contactsView = None

		for path in Dialcentral._glade_files:
			if os.path.isfile(path):
				self._widgetTree = gtk.glade.XML(path)
				break
		else:
			self.display_error_message("Cannot find gc_dialer.glade")
			gtk.main_quit()
			return

		self._window = self._widgetTree.get_widget("Dialpad")
		self._notebook = self._widgetTree.get_widget("notebook")

		global hildon
		self._app = None
		self._isFullScreen = False
		if hildon is not None and self._window is gtk.Window:
			warnings.warn("Hildon installed but glade file not updated to work with hildon", UserWarning, 2)
			hildon = None
		elif hildon is not None:
			self._app = hildon.Program()
			self._window = hildon.Window()
			self._widgetTree.get_widget("vbox1").reparent(self._window)
			self._app.add_window(self._window)
			self._widgetTree.get_widget("usernameentry").set_property('hildon-input-mode', 7)
			self._widgetTree.get_widget("passwordentry").set_property('hildon-input-mode', 7|(1 << 29))

			gtkMenu = self._widgetTree.get_widget("dialpad_menubar")
			menu = gtk.Menu()
			for child in gtkMenu.get_children():
				child.reparent(menu)
			self._window.set_menu(menu)
			gtkMenu.destroy()

			self._window.connect("key-press-event", self._on_key_press)
			self._window.connect("window-state-event", self._on_window_state_change)
		else:
			warnings.warn("No Hildon", UserWarning, 2)

		if hildon is not None:
			self._window.set_title("Keypad")
		else:
			self._window.set_title("%s - Keypad" % self.__pretty_app_name__)

		callbackMapping = {
			"on_loginbutton_clicked": self._on_loginbutton_clicked,
			"on_loginclose_clicked": self._on_loginclose_clicked,
			"on_dialpad_quit": self._on_close,
		}
		self._widgetTree.signal_autoconnect(callbackMapping)

		if self._window:
			self._window.connect("destroy", gtk.main_quit)
			self._window.show_all()

		backgroundSetup = threading.Thread(target=self._idle_setup)
		backgroundSetup.setDaemon(True)
		backgroundSetup.start()


	def _idle_setup(self):
		"""
		If something can be done after the UI loads, push it here so it's not blocking the UI
		"""
		try:
			import osso
		except ImportError:
			osso = None
		self._osso = None
		if osso is not None:
			self._osso = osso.Context(Dialcentral.__app_name__, Dialcentral.__version__, False)
			device = osso.DeviceState(self._osso)
			device.set_device_state_callback(self._on_device_state_change, 0)
		else:
			warnings.warn("No OSSO", UserWarning, 2)

		try:
			import conic
		except ImportError:
			conic = None
		self._connection = None
		if conic is not None:
			self._connection = conic.Connection()
			self._connection.connect("connection-event", self._on_connection_change, Dialcentral.__app_magic__)
			self._connection.request_connection(conic.CONNECT_FLAG_NONE)
		else:
			warnings.warn("No Internet Connectivity API ", UserWarning, 2)

		import gc_backend
		import evo_backend
		# import gmail_backend
		# import maemo_backend

		self._gcBackend = gc_backend.GCDialer()
		gtk.gdk.threads_enter()
		try:
			self._dialpad = Dialpad(self._widgetTree)
			self._dialpad.set_number("")
			self._accountView = AccountInfo(self._widgetTree, self._gcBackend)
			self._recentView = RecentCallsView(self._widgetTree, self._gcBackend)
			self._contactsView = ContactsView(self._widgetTree, self._gcBackend)
		finally:
			gtk.gdk.threads_leave()

		self._dialpad.dial = self._on_dial_clicked
		self._recentView.number_selected = self._on_number_selected
		self._contactsView.number_selected = self._on_number_selected

		#This is where the blocking can start
		if self._gcBackend.is_authed():
			gtk.gdk.threads_enter()
			try:
				self._accountView.update()
			finally:
				gtk.gdk.threads_leave()
		else:
			self.attempt_login(2)

		addressBooks = [
			self._gcBackend,
			evo_backend.EvolutionAddressBook(),
		]
		mergedBook = MergedAddressBook(addressBooks, MergedAddressBook.basic_lastname_sorter)
		self._contactsView.append(mergedBook)
		self._contactsView.extend(addressBooks)
		self._contactsView.open_addressbook(*self._contactsView.get_addressbooks().next()[0][0:2])
		gtk.gdk.threads_enter()
		try:
			self._contactsView._init_books_combo()
		finally:
			gtk.gdk.threads_leave()

		callbackMapping = {
			"on_paste": self._on_paste,
			"on_clearcookies_clicked": self._on_clearcookies_clicked,
			"on_notebook_switch_page": self._on_notebook_switch_page,
			"on_about_activate": self._on_about_activate,
		}
		self._widgetTree.signal_autoconnect(callbackMapping)

		return False

	def attempt_login(self, numOfAttempts = 1):
		"""
		@todo Handle user notification better like attempting to login and failed login

		@note Not meant to be called directly, but run as a seperate thread.
		"""
		assert 0 < numOfAttempts, "That was pointless having 0 or less login attempts"

		if not self._deviceIsOnline:
			warnings.warn("Attempted to login while device was offline", UserWarning, 2)
			return False

		if self._gcBackend.is_authed():
			return True

		for x in xrange(numOfAttempts):
			gtk.gdk.threads_enter()
			try:
				dialog = self._widgetTree.get_widget("login_dialog")
				dialog.set_transient_for(self._window)
				dialog.set_default_response(0)
				dialog.run()

				username = self._widgetTree.get_widget("usernameentry").get_text()
				password = self._widgetTree.get_widget("passwordentry").get_text()
				self._widgetTree.get_widget("passwordentry").set_text("")
				dialog.hide()
			finally:
				gtk.gdk.threads_leave()
			loggedIn = self._gcBackend.login(username, password)
			if loggedIn:
				gtk.gdk.threads_enter()
				try:
					if self._gcBackend.get_callback_number() is None:
						self._gcBackend.set_sane_callback()
					self._accountView.update()
				finally:
					gtk.gdk.threads_leave()
				return True

		return False

	def display_error_message(self, msg):
		error_dialog = gtk.MessageDialog(None, 0, gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE, msg)

		def close(dialog, response, editor):
			editor.about_dialog = None
			dialog.destroy()
		error_dialog.connect("response", close, self)
		error_dialog.run()

	@staticmethod
	def _on_close(*args, **kwds):
		gtk.main_quit()

	def _on_device_state_change(self, shutdown, save_unsaved_data, memory_low, system_inactivity, message, userData):
		"""
		For shutdown or save_unsaved_data, our only state is cookies and I think the cookie manager handles that for us.
		For system_inactivity, we have no background tasks to pause

		@note Hildon specific
		"""
		if memory_low:
			self._gcBackend.clear_caches()
			self._contactsView.clear_caches()
			gc.collect()

	def _on_connection_change(self, connection, event, magicIdentifier):
		"""
		@note Hildon specific
		"""
		import conic

		status = event.get_status()
		error = event.get_error()
		iap_id = event.get_iap_id()
		bearer = event.get_bearer_type()

		if status == conic.STATUS_CONNECTED:
			self._window.set_sensitive(True)
			self._deviceIsOnline = True
			backgroundLogin = threading.Thread(target=self.attempt_login, args=[2])
			backgroundLogin.setDaemon(True)
			backgroundLogin.start()
		elif status == conic.STATUS_DISCONNECTED:
			self._window.set_sensitive(False)
			self._deviceIsOnline = False

	def _on_window_state_change(self, widget, event, *args):
		"""
		@note Hildon specific
		"""
		if event.new_window_state & gtk.gdk.WINDOW_STATE_FULLSCREEN:
			self._isFullScreen = True
		else:
			self._isFullScreen = False

	def _on_key_press(self, widget, event, *args):
		"""
		@note Hildon specific
		"""
		if event.keyval == gtk.keysyms.F6:
			if self._isFullScreen:
				self._window.unfullscreen()
			else:
				self._window.fullscreen()

	def _on_loginbutton_clicked(self, *args):
		self._widgetTree.get_widget("login_dialog").response(gtk.RESPONSE_OK)

	def _on_loginclose_clicked(self, *args):
		self._on_close()
		sys.exit(0)

	def _on_clearcookies_clicked(self, *args):
		self._gcBackend.logout()
		self._accountView.clear()
		self._recentView.clear()
		self._contactsView.clear()

		# re-run the inital grandcentral setup
		backgroundLogin = threading.Thread(target=self.attempt_login, args=[2])
		backgroundLogin.setDaemon(True)
		backgroundLogin.start()

	def _on_notebook_switch_page(self, notebook, page, page_num):
		if page_num == 1:
			self._contactsView.update()
		elif page_num == 3:
			self._recentView.update()

		tabTitle = self._notebook.get_tab_label(self._notebook.get_nth_page(page_num)).get_text()
		if hildon is not None:
			self._window.set_title(tabTitle)
		else:
			self._window.set_title("%s - %s" % (self.__pretty_app_name__, tabTitle))

	def _on_number_selected(self, number):
		self._dialpad.set_number(number)
		self._notebook.set_current_page(0)

	def _on_dial_clicked(self, number):
		"""
		@todo Potential blocking on web access, maybe we should defer parts of this or put up a dialog?
		"""
		loggedIn = self._gcBackend.is_authed()
		if not loggedIn:
			return
			#loggedIn = self.attempt_login(2)

		if not loggedIn or not self._gcBackend.is_authed() or self._gcBackend.get_callback_number() == "":
			self.display_error_message("Backend link with grandcentral is not working, please try again")
			warnings.warn("Backend Status: Logged in? %s, Authenticated? %s, Callback=%s" % (loggedIn, self._gcBackend.is_authed(), self._gcBackend.get_callback_number()), UserWarning, 2)
			return

		try:
			callSuccess = self._gcBackend.dial(number)
		except ValueError, e:
			self._gcBackend._msg = e.message
			callSuccess = False

		if not callSuccess:
			self.display_error_message(self._gcBackend._msg)
		else:
			self._dialpad.clear()

		self._recentView.clear()

	def _on_paste(self, *args):
		contents = self._clipboard.wait_for_text()
		phoneNumber = make_ugly(contents)
		self._dialpad.set_number(phoneNumber)

	def _on_about_activate(self, *args):
		dlg = gtk.AboutDialog()
		dlg.set_name(self.__pretty_app_name__)
		dlg.set_version(self.__version__)
		dlg.set_copyright("Copyright 2008 - LGPL")
		dlg.set_comments("Dialer is designed to interface with your Google Grandcentral account.  This application is not affiliated with Google or Grandcentral in any way")
		dlg.set_website("http://gc-dialer.garage.maemo.org/")
		dlg.set_authors(["<z2n@merctech.com>", "Eric Warnke <ericew@gmail.com>", "Ed Page <edpage@byu.net>"])
		dlg.run()
		dlg.destroy()


def run_doctest():
	import doctest

	failureCount, testCount = doctest.testmod()
	if not failureCount:
		print "Tests Successful"
		sys.exit(0)
	else:
		sys.exit(1)


def run_dialpad():
	gtk.gdk.threads_init()
	if hildon is not None:
		gtk.set_application_name(Dialcentral.__pretty_app_name__)
	handle = Dialcentral()
	gtk.main()


class DummyOptions(object):

	def __init__(self):
		self.test = False


if __name__ == "__main__":
	if len(sys.argv) > 1:
		try:
			import optparse
		except ImportError:
			optparse = None

		if optparse is not None:
			parser = optparse.OptionParser()
			parser.add_option("-t", "--test", action="store_true", dest="test", help="Run tests")
			(commandOptions, commandArgs) = parser.parse_args()
	else:
		commandOptions = DummyOptions()
		commandArgs = []

	if commandOptions.test:
		run_doctest()
	else:
		run_dialpad()
