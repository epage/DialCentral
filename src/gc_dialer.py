#!/usr/bin/python

# GC Dialer - Front end for Google's Grand Central service.
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
Grandcentral Dialer
"""


import sys
import gc
import os
import threading
import time
import re
import warnings

import gobject
import gtk
import gtk.glade

try:
	import hildon
except ImportError:
	hildon = None

try:
	import osso
except ImportError:
	osso = None

try:
	import conic
except ImportError:
	conic = None

try:
	import doctest
	import optparse
except ImportError:
	doctest = None
	optparse = None

from gc_backend import GCDialer
from evo_backend import EvolutionAddressBook

import socket


socket.setdefaulttimeout(5)


def make_ugly(prettynumber):
	"""
	function to take a phone number and strip out all non-numeric
	characters

	>>> make_ugly("+012-(345)-678-90")
	'01234567890'
	"""
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
	if phonenumber is None:
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

	def get_addressbooks(self):
		"""
		@returns Iterable of (Address Book Factory, Book Id, Book Name)
		"""
		yield self, "", "None"
	
	def open_addressbook(self, bookId):
		return self

	@staticmethod
	def factory_short_name():
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

	__pretty_app_name__ = "Dialer"
	__app_name__ = "gc_dialer"
	__version__ = "0.8.0"
	__app_magic__ = 0xdeadbeef

	_glade_files = [
		'./gc_dialer.glade',
		'../lib/gc_dialer.glade',
		'/usr/local/lib/gc_dialer.glade',
	]

	def __init__(self):
		self._phonenumber = ""
		self._prettynumber = ""
		self._areacode = "518"

		self._clipboard = gtk.clipboard_get()

		self._deviceIsOnline = True
		self._callbackList = None
		self._callbackNeedsSetup = True

		self._recenttime = 0.0
		self._recentmodel = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
		self._recentviewselection = None

		self._contactstime = 0.0
		self._contactsmodel = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
		self._contactsviewselection = None

		for path in Dialpad._glade_files:
			if os.path.isfile(path):
				self._widgetTree = gtk.glade.XML(path)
				break
		else:
			self.display_error_message("Cannot find gc_dialer.glade")
			gtk.main_quit()
			return

		aboutHeader = self._widgetTree.get_widget("about_title")
		aboutHeader.set_label("%s\nVersion %s" % (aboutHeader.get_label(), Dialpad.__version__))

		#Get the buffer associated with the number display
		self._numberdisplay = self._widgetTree.get_widget("numberdisplay")
		self.set_number("")
		self._notebook = self._widgetTree.get_widget("notebook")

		self._window = self._widgetTree.get_widget("Dialpad")

		global hildon
		self._app = None
		self._isFullScreen = False
		if hildon is not None and self._window is gtk.Window:
			warnings.warn("Hildon installed but glade file not updated to work with hildon", UserWarning, 2)
			hildon = None
		elif hildon is not None:
			self._app = hildon.Program()
			self._app.add_window(self._window)
			self._widgetTree.get_widget("callbackcombo").get_child().set_property('hildon-input-mode', (1 << 4))
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

		self._osso = None
		if osso is not None:
			self._osso = osso.Context(Dialpad.__app_name__, Dialpad.__version__, False)
			device = osso.DeviceState(self._osso)
			device.set_device_state_callback(self._on_device_state_change, 0)
		else:
			warnings.warn("No OSSO", UserWarning, 2)

		self._connection = None
		if conic is not None:
			self._connection = conic.Connection()
			self._connection.connect("connection-event", self._on_connection_change, Dialpad.__app_magic__)
			self._connection.request_connection(conic.CONNECT_FLAG_NONE)
		else:
			warnings.warn("No Internet Connectivity API ", UserWarning, 2)

		callbackMapping = {
			# Process signals from buttons
			"on_loginbutton_clicked": self._on_loginbutton_clicked,
			"on_loginclose_clicked": self._on_loginclose_clicked,

			"on_dialpad_quit": self._on_close,
			"on_paste": self._on_paste,
			"on_clear_number": self._on_clear_number,

			"on_clearcookies_clicked": self._on_clearcookies_clicked,
			"on_notebook_switch_page": self._on_notebook_switch_page,
			"on_recentview_row_activated": self._on_recentview_row_activated,
			"on_contactsview_row_activated" : self._on_contactsview_row_activated,

			"on_digit_clicked": self._on_digit_clicked,
			"on_back_clicked": self._on_backspace,
			"on_dial_clicked": self._on_dial_clicked,
		}
		self._widgetTree.signal_autoconnect(callbackMapping)
		self._widgetTree.get_widget("callbackcombo").get_child().connect("changed", self._on_callbackentry_changed)
		self._widgetTree.get_widget("addressbook_combo").get_child().connect("changed", self._on_addressbook_entry_changed)

		if self._window:
			self._window.connect("destroy", gtk.main_quit)
			self._window.show_all()

		self._gcBackend = GCDialer()

		self._addressBookFactories = [
			DummyAddressBook(),
			EvolutionAddressBook(),
			self._gcBackend,
		]
		self._addressBook = None
		self.open_addressbook(*self.get_addressbooks().next()[0][0:2])

		self._booksList = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
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

		combobox = self._widgetTree.get_widget("addressbook_combo")
		combobox.set_model(self._booksList)
		combobox.set_text_column(2)
		combobox.set_active(0)

		self._phoneTypeSelector = PhoneTypeSelector(self._widgetTree, self._gcBackend)

		self._init_recent_view()
		self._init_contacts_view()
		if self._gcBackend.is_authed():
			self.set_account_number()
		else:
			self.attempt_login(2)

	def _init_recent_view(self):
		recentview = self._widgetTree.get_widget("recentview")
		recentview.set_model(self._recentmodel)
		textrenderer = gtk.CellRendererText()

		# Add the column to the treeview
		column = gtk.TreeViewColumn("Calls", textrenderer, text=1)
		column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)

		recentview.append_column(column)

		self._recentviewselection = recentview.get_selection()
		self._recentviewselection.set_mode(gtk.SELECTION_SINGLE)

		return False

	def _init_contacts_view(self):
		contactsview = self._widgetTree.get_widget("contactsview")
		contactsview.set_model(self._contactsmodel)

		# Add the column to the treeview
		column = gtk.TreeViewColumn("Contact")

		textrenderer = gtk.CellRendererText()
		column.pack_start(textrenderer, expand=True)
		column.add_attribute(textrenderer, 'text', 1)

		textrenderer = gtk.CellRendererText()
		column.pack_start(textrenderer, expand=True)
		column.add_attribute(textrenderer, 'text', 4)

		column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
		column.set_sort_column_id(1)
		column.set_visible(True)
		contactsview.append_column(column)

		#textrenderer = gtk.CellRendererText()
		#column = gtk.TreeViewColumn("Location", textrenderer, text=2)
		#column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
		#column.set_sort_column_id(2)
		#column.set_visible(True)
		#contactsview.append_column(column)

		#textrenderer = gtk.CellRendererText()
		#column = gtk.TreeViewColumn("Phone", textrenderer, text=3)
		#column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
		#column.set_sort_column_id(3)
		#column.set_visible(True)
		#contactsview.append_column(column)

		self._contactsviewselection = contactsview.get_selection()
		self._contactsviewselection.set_mode(gtk.SELECTION_SINGLE)

		return False

	def _idly_populate_callback_combo(self):
		self._callbackList = gtk.ListStore(gobject.TYPE_STRING)
		for number, description in self._gcBackend.get_callback_numbers().iteritems():
			self._callbackList.append((make_pretty(number),))

		combobox = self._widgetTree.get_widget("callbackcombo")
		combobox.set_model(self._callbackList)
		combobox.set_text_column(0)

		combobox.get_child().set_text(make_pretty(self._gcBackend.get_callback_number()))
		self._callbackNeedsSetup = False

	def _idly_populate_recentview(self):
		self._recentmodel.clear()

		for personsName, phoneNumber, date, action in self._gcBackend.get_recent():
			description = "%s on %s from/to %s - %s" % (action.capitalize(), date, personsName, phoneNumber)
			item = (phoneNumber, description)
			self._recentmodel.append(item)

		self._recenttime = time.time()
		return False

	@make_idler
	def _idly_populate_contactsview(self):
		self._contactsmodel.clear()

		# completely disable updating the treeview while we populate the data
		contactsview = self._widgetTree.get_widget("contactsview")
		contactsview.freeze_child_notify()
		contactsview.set_model(None)

		contactType = (self._addressBook.factory_short_name(),)
		for contactId, contactName in self._addressBook.get_contacts():
			self._contactsmodel.append(contactType + (contactName, "", contactId) + ("",))
			yield

		# restart the treeview data rendering
		contactsview.set_model(self._contactsmodel)
		contactsview.thaw_child_notify()

		self._contactstime = time.time()

	def attempt_login(self, numOfAttempts = 1):
		"""
		@note Assumes that you are already logged in
		"""
		assert 0 < numOfAttempts, "That was pointless having 0 or less login attempts"

		if not self._deviceIsOnline:
			warnings.warn("Attempted to login while device was offline", UserWarning, 2)
			return False

		dialog = self._widgetTree.get_widget("login_dialog")
		for i in range(numOfAttempts):
			dialog.run()

			username = self._widgetTree.get_widget("usernameentry").get_text()
			password = self._widgetTree.get_widget("passwordentry").get_text()
			self._widgetTree.get_widget("passwordentry").set_text("")

			loggedIn = self._gcBackend.login(username, password)
			dialog.hide()
			if loggedIn:
				if self._gcBackend.get_callback_number() is None:
					self._gcBackend.set_sane_callback()
				self.set_account_number()
				return True

		return False

	def display_error_message(self, msg):
		error_dialog = gtk.MessageDialog(None, 0, gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE, msg)

		def close(dialog, response, editor):
			editor.about_dialog = None
			dialog.destroy()
		error_dialog.connect("response", close, self)
		error_dialog.run()

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
		gobject.idle_add(self._idly_populate_contactsview)

	def set_number(self, number):
		"""
		Set the callback phonenumber
		"""
		self._phonenumber = make_ugly(number)
		self._prettynumber = make_pretty(self._phonenumber)
		self._numberdisplay.set_label("<span size='30000' weight='bold'>%s</span>" % (self._prettynumber))

	def set_account_number(self):
		"""
		Displays current account number
		"""
		accountnumber = self._gcBackend.get_account_number()
		self._widgetTree.get_widget("gcnumber_display").set_label("<span size='23000' weight='bold'>%s</span>" % (accountnumber))

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
			re.purge()
			gc.collect()

	def _on_connection_change(self, connection, event, magicIdentifier):
		"""
		@note Hildon specific
		"""
		status = event.get_status()
		error = event.get_error()
		iap_id = event.get_iap_id()
		bearer = event.get_bearer_type()

		if status == conic.STATUS_CONNECTED:
			self._window.set_sensitive(True)
			self._deviceIsOnline = True
			if not self._gcBackend.is_authed():
				self.attempt_login(2)
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
		self._callbackNeedsSetup = True
		self._recenttime = 0.0
		self._contactstime = 0.0
		self._recentmodel.clear()
		self._widgetTree.get_widget("callbackcombo").get_child().set_text("")

		# re-run the inital grandcentral setup
		self.attempt_login(2)
		gobject.idle_add(self._idly_populate_callback_combo)

	def _on_callbackentry_changed(self, *args):
		"""
		@todo Potential blocking on web access, maybe we should defer this or put up a dialog?
		"""
		text = make_ugly(self._widgetTree.get_widget("callbackcombo").get_child().get_text())
		if not self._gcBackend.is_valid_syntax(text):
			warnings.warn("%s is not a valid callback number" % text, UserWarning, 2)
		elif text == self._gcBackend.get_callback_number():
			warnings.warn("Callback number already is %s" % self._gcBackend.get_callback_number(), UserWarning, 2)
		else:
			self._gcBackend.set_callback_number(text)

	def _on_recentview_row_activated(self, treeview, path, view_column):
		model, itr = self._recentviewselection.get_selected()
		if not itr:
			return

		self.set_number(self._recentmodel.get_value(itr, 0))
		self._notebook.set_current_page(0)
		self._recentviewselection.unselect_all()

	def _on_addressbook_entry_changed(self, *args, **kwds):
		combobox = self._widgetTree.get_widget("addressbook_combo")
		itr = combobox.get_active_iter()

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
			self.set_number(phoneNumber)
			self._notebook.set_current_page(0)

		self._contactsviewselection.unselect_all()

	def _on_notebook_switch_page(self, notebook, page, page_num):
		if page_num == 1 and 300 < (time.time() - self._contactstime):
			gobject.idle_add(self._idly_populate_contactsview)
		elif page_num == 2 and 300 < (time.time() - self._recenttime):
			gobject.idle_add(self._idly_populate_recentview)
		elif page_num == 3 and self._callbackNeedsSetup:
			gobject.idle_add(self._idly_populate_callback_combo)

		tabTitle = self._notebook.get_tab_label(self._notebook.get_nth_page(page_num)).get_text()
		if hildon is not None:
			self._window.set_title(tabTitle)
		else:
			self._window.set_title("%s - %s" % (self.__pretty_app_name__, tabTitle))

	def _on_dial_clicked(self, widget):
		"""
		@todo Potential blocking on web access, maybe we should defer parts of this or put up a dialog?
		"""
		loggedIn = self._gcBackend.is_authed()
		if not loggedIn:
			loggedIn = self.attempt_login(2)

		if not loggedIn or not self._gcBackend.is_authed() or self._gcBackend.get_callback_number() == "":
			self.display_error_message("Backend link with grandcentral is not working, please try again")
			warnings.warn("Backend Status: Logged in? %s, Authenticated? %s, Callback=%s" % (loggedIn, self._gcBackend.is_authed(), self._gcBackend.get_callback_number()), UserWarning, 2)
			return

		try:
			callSuccess = self._gcBackend.dial(self._phonenumber)
		except ValueError, e:
			self._gcBackend._msg = e.message
			callSuccess = False

		if not callSuccess:
			self.display_error_message(self._gcBackend._msg)
		else:
			self.set_number("")

		self._recentmodel.clear()
		self._recenttime = 0.0

	def _on_paste(self, *args):
		contents = self._clipboard.wait_for_text()
		phoneNumber = re.sub('\D', '', contents)
		self.set_number(phoneNumber)

	def _on_clear_number(self, *args):
		self.set_number("")

	def _on_digit_clicked(self, widget):
		self.set_number(self._phonenumber + widget.get_name()[5])

	def _on_backspace(self, widget):
		self.set_number(self._phonenumber[:-1])


def run_doctest():
	failureCount, testCount = doctest.testmod()
	if not failureCount:
		print "Tests Successful"
		sys.exit(0)
	else:
		sys.exit(1)


def run_dialpad():
	gtk.gdk.threads_init()
	title = 'Dialpad'
	handle = Dialpad()
	gtk.main()


class DummyOptions(object):

	def __init__(self):
		self.test = False


if __name__ == "__main__":
	if hildon is not None:
		gtk.set_application_name(Dialpad.__pretty_app_name__)

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
