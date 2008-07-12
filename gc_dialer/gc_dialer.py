#!/usr/bin/python2.5


"""
Grandcentral Dialer
Python front-end to a wget script to use grandcentral.com to place outbound VOIP calls.
(C) 2008 Mark Bergman
bergman@merctech.com
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
	try:
		import abook
		import evolution.ebook as evobook
	except ImportError:
		abook = None
		evobook = None
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

from gcbackend import GCDialer

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


class Dialpad(object):

	__app_name__ = "gc_dialer"
	__version__ = "0.7.0"
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
		self._callbackNeedsSetup = True
		self._recenttime = 0.0
		self._recentmodel = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
		self._recentviewselection = None

		for path in Dialpad._glade_files:
			if os.path.isfile(path):
				self._widgetTree = gtk.glade.XML(path)
				break
		else:
			self.display_error_message("Cannot find gc_dialer.glade")
			gtk.main_quit()
			return

		self._widgetTree.get_widget("about_title").set_label(self._widgetTree.get_widget("about_title").get_label()+"\nVersion "+Dialpad.__version__)

		#Get the buffer associated with the number display
		self._numberdisplay = self._widgetTree.get_widget("numberdisplay")
		self.set_number("")
		self._notebook = self._widgetTree.get_widget("notebook")

		self._window = self._widgetTree.get_widget("Dialpad")

		global hildon
		self._app = None
		self._isFullScreen = False
		if hildon is not None and isinstance(self._window, gtk.Window):
			warnings.warn("Hildon installed but glade file not updated to work with hildon", UserWarning, 2)
			hildon = None
		elif hildon is not None:
			self._app = hildon.Program()
			self._window.set_title("Keypad")
			self._app.add_window(self._window)
			self._widgetTree.get_widget("callbackcombo").get_child().set_property('hildon-input-mode', (1 << 4))
			self._widgetTree.get_widget("usernameentry").set_property('hildon-input-mode', 7)
			self._widgetTree.get_widget("passwordentry").set_property('hildon-input-mode', 7|(1 << 29))

			gtkMenu = self._widgetTree.get_widget("menubar1")
			menu = gtk.Menu()
			for child in gtkMenu.get_children():
				child.reparent(menu)
			self._window.set_menu(menu)
			gtkMenu.destroy()

			self._window.connect("key-press-event", self._on_key_press)
			self._window.connect("window-state-event", self._on_window_state_change)
		else:
			warnings.warn("No Hildon", UserWarning, 2)

		self._osso = None
		self._ebook = None
		if osso is not None:
			self._osso = osso.Context(Dialpad.__app_name__, Dialpad.__version__, False)
			device = osso.DeviceState(self._osso)
			device.set_device_state_callback(self._on_device_state_change, 0)
			if abook is not None and evobook is not None:
				abook.init_with_name(Dialpad.__app_name__, self._osso)
				self._ebook = evobook.open_addressbook("default")
			else:
				warnings.warn("No abook and No evolution address book support", UserWarning, 2)
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

			"on_dialpad_quit": (lambda data: gtk.main_quit()),
			"on_paste": self._on_paste,
			"on_clear_number": self._on_clear_number,

			"on_clearcookies_clicked": self._on_clearcookies_clicked,
			"on_notebook_switch_page": self._on_notebook_switch_page,
			"on_recentview_row_activated": self._on_recentview_row_activated,

			"on_digit_clicked": self._on_digit_clicked,
			"on_back_clicked": self._on_backspace,
			"on_dial_clicked": self._on_dial_clicked,
		}
		self._widgetTree.signal_autoconnect(callbackMapping)

		if self._window:
			self._window.connect("destroy", gtk.main_quit)
			self._window.show_all()

		self._gcBackend = GCDialer()

		self.attempt_login(2)
		gobject.idle_add(self._init_grandcentral)
		# Defer initalization of recent view
		gobject.idle_add(self._init_recent_view)

	def _init_grandcentral(self):
		""" Deferred initalization of the grandcentral info """

		if self._gcBackend.is_authed():
			if self._gcBackend.get_callback_number() is None:
				self._gcBackend.set_sane_callback()
			self.set_account_number()

		return False

	def _init_recent_view(self):
		""" Deferred initalization of the recent view treeview """

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

	def _setup_callback_combo(self):
		combobox = self._widgetTree.get_widget("callbackcombo")
		self.callbacklist = gtk.ListStore(gobject.TYPE_STRING)
		combobox.set_model(self.callbacklist)
		combobox.set_text_column(0)
		for number, description in self._gcBackend.get_callback_numbers().iteritems():
			self.callbacklist.append([make_pretty(number)] )

		self._widgetTree.get_widget("callbackcombo").get_child().set_text(make_pretty(self._gcBackend.get_callback_number()))
		self._callbackNeedsSetup = False

	def populate_recentview(self):
		self._recentmodel.clear()
		for personsName, phoneNumber, date, action in self._gcBackend.get_recent():
			item = (phoneNumber, "%s on %s from/to %s - %s" % (action.capitalize(), date, personsName, phoneNumber))
			self._recentmodel.append(item)
		self._recenttime = time.time()

		return False

	def attempt_login(self, times = 1):
		assert 0 < times, "That was pointless having 0 or less login attempts"
		dialog = self._widgetTree.get_widget("login_dialog")

		while (0 < times) and not self._gcBackend.is_authed():
			dialog.run()

			username = self._widgetTree.get_widget("usernameentry").get_text()
			password = self._widgetTree.get_widget("passwordentry").get_text()
			self._widgetTree.get_widget("passwordentry").set_text("")

			loggedIn = self._gcBackend.login(username, password)
			dialog.hide()
			if loggedIn:
				return True
			times -= 1

		return False

	def display_error_message(self, msg):
		error_dialog = gtk.MessageDialog(None, 0, gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE, msg)

		def close(dialog, response, editor):
			editor.about_dialog = None
			dialog.destroy()
		error_dialog.connect("response", close, self)
		error_dialog.run()

	def set_number(self, number):
		self._phonenumber = make_ugly(number)
		self._prettynumber = make_pretty(self._phonenumber)
		self._numberdisplay.set_label("<span size='30000' weight='bold'>%s</span>" % ( self._prettynumber ) )

	def set_account_number(self):
		accountnumber = self._gcBackend.get_account_number()
		self._widgetTree.get_widget("gcnumberlabel").set_label("<span size='23000' weight='bold'>%s</span>" % (accountnumber))

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

	def _on_loginbutton_clicked(self, data=None):
		self._widgetTree.get_widget("login_dialog").response(gtk.RESPONSE_OK)

	def _on_loginclose_clicked(self, data=None):
		sys.exit(0)

	def _on_clearcookies_clicked(self, data=None):
		self._gcBackend.reset()
		self._callbackNeedsSetup = True
		self._recenttime = 0.0
		self._recentmodel.clear()
		self._widgetTree.get_widget("callbackcombo").get_child().set_text("")

		# re-run the inital grandcentral setup
		self.attempt_login(2)
		gobject.idle_add(self._init_grandcentral)

	def _on_callbackentry_changed(self, data=None):
		"""
		@todo Potential blocking on web access, maybe we should defer this or put up a dialog?
		"""
		text = make_ugly(self._widgetTree.get_widget("callbackcombo").get_child().get_text())
		if self._gcBackend.is_valid_syntax(text) and text != self._gcBackend.get_callback_number():
			self._gcBackend.set_callback_number(text)

	def _on_recentview_row_activated(self, treeview, path, view_column):
		model, itr = self._recentviewselection.get_selected()
		if not itr:
			return

		self.set_number(self._recentmodel.get_value(itr, 0))
		self._notebook.set_current_page(0)
		self._recentviewselection.unselect_all()

	def _on_notebook_switch_page(self, notebook, page, page_num):
		if page_num == 1 and (time.time() - self._recenttime) > 300:
			gobject.idle_add(self.populate_recentview)
		elif page_num ==2 and self._callbackNeedsSetup:
			gobject.idle_add(self._setup_callback_combo)

		if hildon:
			self._window.set_title(self._notebook.get_tab_label(self._notebook.get_nth_page(page_num)).get_text())

	def _on_dial_clicked(self, widget):
		"""
		@todo Potential blocking on web access, maybe we should defer parts of this or put up a dialog?
		"""
		loggedIn = self.attempt_login(2)
		if not loggedIn or not self._gcBackend.is_authed() or self._gcBackend.get_callback_number() == "":
			self.display_error_message("Backend link with grandcentral is not working, please try again")
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

	def _on_paste(self, data=None):
		contents = self._clipboard.wait_for_text()
		phoneNumber = re.sub('\D', '', contents)
		self.set_number(phoneNumber)

	def _on_clear_number(self, data=None):
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
	sys.exit(0)


class DummyOptions(object):

	def __init__(self):
		self.test = False


if __name__ == "__main__":
	if hildon is not None:
		gtk.set_application_name("Dialer")

	if optparse is not None:
		parser = optparse.OptionParser()
		parser.add_option("-t", "--test", action="store_true", dest="test", help="Run tests")
		(options, args) = parser.parse_args()
	else:
		args = []
		options = DummyOptions()

	if options.test:
		run_doctest()
	else:
		run_dialpad()
