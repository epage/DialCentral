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
	import doctest
	import optparse
except ImportError:
	doctest = None
	optparse = None

from gcbackend import GCDialer

import socket


socket.setdefaulttimeout(5)


def makeugly(prettynumber):
	"""
	function to take a phone number and strip out all non-numeric
	characters

	>>> makeugly("+012-(345)-678-90")
	'01234567890'
	"""
	uglynumber = re.sub('\D', '', prettynumber)
	return uglynumber


def makepretty(phonenumber):
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
	>>> makepretty("12")
	'12'
	>>> makepretty("1234567")
	'123-4567'
	>>> makepretty("2345678901")
	'(234)-567-8901'
	>>> makepretty("12345678901") 	 
	'1 (234)-567-8901'
	>>> makepretty("01234567890")
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
		prettynumber = "1 (%s)-%s-%s" %(phonenumber[1:4], phonenumber[4:7], phonenumber[7:]) 
	elif len(phonenumber) > 7:
		prettynumber = "(%s)-%s-%s" % (phonenumber[0:3], phonenumber[3:6], phonenumber[6:])
	return prettynumber


class Dialpad(object):

	__app_name__ = "gc_dialer"
	__version__ = "0.7.0"

	_glade_files = [
		'./gc_dialer.glade',
		'../lib/gc_dialer.glade',
		'/usr/local/lib/gc_dialer.glade',
	]

	def __init__(self):
		self.phonenumber = ""
		self.prettynumber = ""
		self.areacode = "518"
		self.clipboard = gtk.clipboard_get()
		self.recentmodel = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
		self.recentviewselection = None
		self.callbackNeedsSetup = True
		self.recenttime = 0.0

		for path in Dialpad._glade_files:
			if os.path.isfile(path):
				self.wTree = gtk.glade.XML(path)
				break
		else:
			self.ErrPopUp("Cannot find gc_dialer.glade")
			gtk.main_quit()
			return

		self.wTree.get_widget("about_title").set_label(self.wTree.get_widget("about_title").get_label()+"\nVersion "+Dialpad.__version__)

		#Get the buffer associated with the number display
		self.numberdisplay = self.wTree.get_widget("numberdisplay")
		self.setNumber("")
		self.notebook = self.wTree.get_widget("notebook")

		self.window = self.wTree.get_widget("Dialpad")

		global hildon
		self.app = None
		if hildon is not None and isinstance(self.window, gtk.Window):
			warnings.warn("Hildon installed but glade file not updated to work with hildon", UserWarning, 2)
			hildon = None
		elif hildon is not None:
			self.app = hildon.Program()
			self.window.set_title("Keypad")
			self.app.add_window(self.window)
			self.wTree.get_widget("callbackcombo").get_child().set_property('hildon-input-mode', (1 << 4))
			self.wTree.get_widget("usernameentry").set_property('hildon-input-mode', 7)
			self.wTree.get_widget("passwordentry").set_property('hildon-input-mode', 7|(1 << 29))
		else:
			warnings.warn("No Hildon", UserWarning, 2)

		if osso is not None:
			self.osso = osso.Context(__name__, Dialpad.__version__, False)
			device = osso.DeviceState(self.osso)
			device.set_device_state_callback(self.on_device_state_change, 0)
			if abook is not None and evobook is not None:
				abook.init_with_name(__name__, self.osso)
				self.ebook = evo.open_addressbook("default")
			else:
				warnings.warn("No abook and No evolution address book support", UserWarning, 2)
		else:
			warnings.warn("No OSSO", UserWarning, 2)

		if self.window:
			self.window.connect("destroy", gtk.main_quit)
			self.window.show_all()

		callbackMapping = {
			# Process signals from buttons
			"on_digit_clicked"  : self.on_digit_clicked,
			"on_dial_clicked"    : self.on_dial_clicked,
			"on_loginbutton_clicked" : self.on_loginbutton_clicked,
			"on_loginclose_clicked" : self.on_loginclose_clicked,
			"on_clearcookies_clicked" : self.on_clearcookies_clicked,
			"on_notebook_switch_page" : self.on_notebook_switch_page,
			"on_recentview_row_activated" : self.on_recentview_row_activated,
			"on_back_clicked" : self.Backspace
		}
		self.wTree.signal_autoconnect(callbackMapping)
		self.wTree.get_widget("callbackcombo").get_child().connect("changed", self.on_callbackentry_changed)

		# Defer initalization of recent view
		self.gcd = GCDialer()

		self.attemptLogin(2)
		gobject.idle_add(self.init_grandcentral)
		gobject.idle_add(self.init_recentview)

	def init_grandcentral(self):
		""" deferred initalization of the grandcentral info """
		
		try:
			if self.gcd.isAuthed():
				if self.gcd.getCallbackNumber() is None:
					self.gcd.setSaneCallback()
		except:
			pass
		
		self.setAccountNumber()
		print "exit init_gc"
		return False

	def init_recentview(self):
		""" deferred initalization of the recent view treeview """

		recentview = self.wTree.get_widget("recentview")
		recentview.set_model(self.recentmodel)
		textrenderer = gtk.CellRendererText()

		# Add the column to the treeview
		column = gtk.TreeViewColumn("Calls", textrenderer, text=1)
		column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)

		recentview.append_column(column)

		self.recentviewselection = recentview.get_selection()
		self.recentviewselection.set_mode(gtk.SELECTION_SINGLE)

		return False

	def on_recentview_row_activated(self, treeview, path, view_column):
		model, itr = self.recentviewselection.get_selected()
		if not itr:
			return

		self.setNumber(self.recentmodel.get_value(itr, 0))
		self.notebook.set_current_page(0)
		self.recentviewselection.unselect_all()

	def on_notebook_switch_page(self, notebook, page, page_num):
		if page_num == 1 and (time.time() - self.recenttime) > 300:
			gobject.idle_add(self.populate_recentview)
		elif page_num ==2 and self.callbackNeedsSetup:
			gobject.idle_add(self.setupCallbackCombo)
		if hildon:
			try:
				self.window.set_title(self.notebook.get_tab_label(self.notebook.get_nth_page(page_num)).get_text())
			except:
				self.window.set_title("")

	def populate_recentview(self):
		print "Populating"
		self.recentmodel.clear()
		for item in self.gcd.get_recent():
			self.recentmodel.append(item)
		self.recenttime = time.time()

		return False

	def on_clearcookies_clicked(self, data=None):
		self.gcd.reset()
		self.callbackNeedsSetup = True
		self.recenttime = 0.0
		self.recentmodel.clear()
		self.wTree.get_widget("callbackcombo").get_child().set_text("")
	
		# re-run the inital grandcentral setup
		self.attemptLogin(2)
		gobject.idle_add(self.init_grandcentral)

	def setupCallbackCombo(self):
		combobox = self.wTree.get_widget("callbackcombo")
		self.callbacklist = gtk.ListStore(gobject.TYPE_STRING)
		combobox.set_model(self.callbacklist)
		combobox.set_text_column(0)
		for number, description in self.gcd.getCallbackNumbers().iteritems():
			self.callbacklist.append([makepretty(number)] )

		self.wTree.get_widget("callbackcombo").get_child().set_text(makepretty(self.gcd.getCallbackNumber()))
		self.callbackNeedsSetup = False

	def on_callbackentry_changed(self, data=None):
		text = makeugly(self.wTree.get_widget("callbackcombo").get_child().get_text())
		if self.gcd.validate(text) and text != self.gcd.getCallbackNumber():
			self.gcd.setCallbackNumber(text)

	def attemptLogin(self, times = 1):
		dialog = self.wTree.get_widget("login_dialog")

		while (0 < times) and not self.gcd.isAuthed():
			if dialog.run() != gtk.RESPONSE_OK:
				times = 0
				continue

			username = self.wTree.get_widget("usernameentry").get_text()
			password = self.wTree.get_widget("passwordentry").get_text()
			self.wTree.get_widget("passwordentry").set_text("")
			print "Attempting login"
			self.gcd.login(username, password)
			print "hiding dialog"
			dialog.hide()
			times = times - 1

		return False

	def ErrPopUp(self, msg):
		error_dialog = gtk.MessageDialog(None, 0, gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE, msg)

		def close(dialog, response, editor):
			editor.about_dialog = None
			dialog.destroy()
		error_dialog.connect("response", close, self)
		self.error_dialog = error_dialog
		error_dialog.run()

	def on_paste(self, data=None):
		contents = self.clipboard.wait_for_text()
		phoneNumber = re.sub('\D', '', contents)
		self.setNumber(phoneNumber)
	
	def on_loginbutton_clicked(self, data=None):
		self.wTree.get_widget("login_dialog").response(gtk.RESPONSE_OK)

	def on_loginclose_clicked(self, data=None):
		sys.exit(0)

	def on_dial_clicked(self, widget):
		self.attemptLogin(3)

		if not self.gcd.isAuthed() or self.gcd.getCallbackNumber() == "":
			self.ErrPopUp("Backend link with grandcentral is not working, please try again")
			return

		try:
			callSuccess = self.gcd.dial(self.phonenumber)
		except ValueError, e:
			self.gcd._msg = e.message
			callSuccess = False

		if not callSuccess:
			self.ErrPopUp(self.gcd._msg)
		else:
			self.setNumber("")

		self.recentmodel.clear()
		self.recenttime = 0.0
	
	def on_device_state_change(self, shutdown, save_unsaved_data, memory_low, system_inactivity, message, userData):
		"""
		For shutdown or save_unsaved_data, our only state is cookies and I think the cookie manager handles that for us.
		For system_inactivity, we have no background tasks to pause

		@todo Might be useful to do something when going in offline mode or low memory
		@note Hildon specific
		"""
		if shutdown or save_unsaved_data:
			pass

		if memory_low:
			self.gcd.clear_caches()
			re.purge()
			gc.collect()

	def setNumber(self, number):
		self.phonenumber = makeugly(number)
		self.prettynumber = makepretty(self.phonenumber)
		self.numberdisplay.set_label("<span size='30000' weight='bold'>%s</span>" % ( self.prettynumber ) )

	def setAccountNumber(self):
		accountnumber = self.gcd.getAccountNumber()
		self.wTree.get_widget("gcnumberlabel").set_label("<span size='23000' weight='bold'>%s</span>" % (accountnumber))

	def Backspace(self, widget):
		self.setNumber(self.phonenumber[:-1])

	def on_digit_clicked(self, widget):
		self.setNumber(self.phonenumber + widget.get_name()[5])


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
	if hildon:
		gtk.set_application_name("Dialer")

	try:
		parser = optparse.OptionParser()
		parser.add_option("-t", "--test", action="store_true", dest="test", help="Run tests")
		(options, args) = parser.parse_args()
	except:
		args = []
		options = DummyOptions()

	if options.test:
		run_doctest()
	else:
		run_dialpad()
