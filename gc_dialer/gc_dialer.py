#!/usr/bin/python2.5 

# Grandcentral Dialer
# Python front-end to a wget script to use grandcentral.com to place outbound VOIP calls.
# (C) 2008 Mark Bergman
# bergman@merctech.com

import sys
import os
import re
import time
import gobject
import gtk
import gc
#import hildon

from gcbackend import GCDialer

def makeugly(prettynumber):
	# function to take a phone number and strip out all non-numeric
	# characters
	uglynumber=re.sub('\D','',prettynumber)
	return uglynumber

def makepretty(phonenumber):
	# Function to take a phone number and return the pretty version
	# pretty numbers:
	#	if phonenumber begins with 0:
	#		...-(...)-...-....
	#	else
	#		if phonenumber is 13 digits:
	#			(...)-...-....
	#		else if phonenumber is 10 digits:
	#			...-....
	if phonenumber is None:
		return ""

	if len(phonenumber) < 3 :
		return phonenumber

	if  phonenumber[0] == "0" :
			if len(phonenumber) <=3:
				prettynumber = "+" + phonenumber[0:3] 
			elif len(phonenumber) <=6:
				prettynumber = "+" + phonenumber[0:3] + "-(" + phonenumber[3:6] + ")"
			elif len(phonenumber) <=9:
				prettynumber = "+" + phonenumber[0:3] + "-(" + phonenumber[3:6] + ")-" + phonenumber[6:9]
			else:
				prettynumber = "+" + phonenumber[0:3] + "-(" + phonenumber[3:6] + ")-" + phonenumber[6:9] + "-" + phonenumber[9:]
			return prettynumber
	elif phonenumber[0] == "1" and len(phonenumber) > 8:
		prettynumber = "1 (" + phonenumber[1:4] + ")-" + phonenumber[4:7] + "-" + phonenumber[7:]
		return prettynumber
	elif len(phonenumber) <= 7 :
			prettynumber = phonenumber[0:3] + "-" + phonenumber[3:] 
	elif len(phonenumber) > 7 :
			prettynumber = "(" + phonenumber[0:3] + ")-" + phonenumber[3:6] + "-" + phonenumber[6:]
	return prettynumber

class Dialpad:

	def __init__(self):
		self.phonenumber = ""
		self.prettynumber = ""
		self.areacode = "518"
		self.gcd = GCDialer()
		self.wTree = gtk.Builder()

		for path in [ './gc_dialer.xml',
				'../lib/gc_dialer.xml',
				'/usr/local/lib/gc_dialer.xml' ]:
			if os.path.isfile(path):
				self.wTree.add_from_file(path)
				break

		self.window = self.wTree.get_object("Dialpad")
		#Get the buffer associated with the number display
		self.numberdisplay = self.wTree.get_object("numberdisplay")
		self.setNumber("")

		self.recentview = self.wTree.get_object("recentview")
		self.recentmodel = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
		self.recentview.set_model(self.recentmodel)
		textrenderer = gtk.CellRendererText()

		# Add the column to the treeview
		column = gtk.TreeViewColumn("Calls", textrenderer, text=1)
		column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
		self.recentview.append_column(column)

		self.recentviewselection = self.recentview.get_selection()
		self.recentviewselection.set_mode(gtk.SELECTION_SINGLE)
		self.recenttime = 0.0

		self.notebook = self.wTree.get_object("notebook")

		self.isHildon = False
		#if True:
		try:
			self.app = hildon.Program()
			self.wTree.get_object("callbackentry").set_property('hildon-input-mode', 1|(1 << 4))
			self.isHildon = True
		except:
			print "No hildon"

		if (self.window):
			self.window.connect("destroy", gtk.main_quit)
			self.window.show_all()

		dic = {
			# Process signals from buttons
			"on_digit_clicked"  : self.on_digit_clicked,
			"on_dial_clicked"    : self.on_dial_clicked,
			"on_loginbutton_clicked" : self.on_loginbutton_clicked,
			"on_clearcookies_clicked" : self.on_clearcookies_clicked,
			"on_callbackentry_changed" : self.on_callbackentry_changed,
			"on_notebook_switch_page" : self.on_notebook_switch_page,
			"on_recentview_row_activated" : self.on_recentview_row_activated,
			"on_back_clicked" : self.Backspace }
		self.wTree.connect_signals(dic)

		self.attemptLogin(3)
		if self.gcd.getCallbackNumber() is None:
			self.gcd.setSaneCallback()
		
		self.setAccountNumber()
		self.setupCallbackCombo()
		self.reduce_memory()

	def reduce_memory(self):
		re.purge()
		num = gc.collect()
		#print "collect %d objects" % ( num )

	def on_recentview_row_activated(self, treeview, path, view_column):
		model, iter = self.recentviewselection.get_selected()
		if iter:
			self.setNumber(self.recentmodel.get_value(iter,0))
			self.notebook.set_current_page(0)
			self.recentviewselection.unselect_all()

	def on_notebook_switch_page(self, notebook, page, page_num):
		if page_num == 1 and (time.time() - self.recenttime) > 300:
			self.populate_recentview()

	def populate_recentview(self):
		print "Populating"
		self.recentmodel.clear()
		for item in self.gcd.get_recent():
			self.recentmodel.append(item)
		self.recenttime = time.time()

	def on_clearcookies_clicked(self, data=None):
		self.gcd.reset()
		self.attemptLogin(3)

	def setupCallbackCombo(self):
		combobox = self.wTree.get_object("callbackcombo")
		self.callbacklist = gtk.ListStore(gobject.TYPE_STRING)
		combobox.set_model(self.callbacklist)
		combobox.set_text_column(0)
		for k,v in self.gcd.getCallbackNumbers().iteritems():
			self.callbacklist.append([makepretty(k)] )
		
		self.wTree.get_object("callbackentry").set_text(makepretty(self.gcd.getCallbackNumber()))

	def on_callbackentry_changed(self, data=None):
		text = makeugly(self.wTree.get_object("callbackentry").get_text())
		if self.gcd.validate(text) and text != self.gcd.getCallbackNumber():
			self.gcd.setCallbackNumber(text)
			self.wTree.get_object("callbackentry").set_text(self.wTree.get_object("callbackentry").get_text())
		self.reduce_memory()


	def attemptLogin(self, times = 1):
		if self.isHildon:
			dialog = hildon.LoginDialog(self.window)
			dialog.set_message("Grandcentral Login")
		else:
			dialog = self.wTree.get_object("login_dialog")

		while ( (times > 0) and (self.gcd.isAuthed() == False) ):
			if dialog.run() == gtk.RESPONSE_OK:
				if self.isHildon:
					username = dialog.get_username()
					password = dialog.get_password()
				else:
					username = self.wTree.get_object("usernameentry").get_text()
					password = self.wTree.get_object("passwordentry").get_text()
					self.wTree.get_object("passwordentry").set_text("")
				self.gcd.login(username, password)
				dialog.hide()
				times = times - 1
			else:
				times = 0

		if self.isHildon:
			dialog.destroy()

	def ErrPopUp(self,msg):
		error_dialog = gtk.MessageDialog(None,0,gtk.MESSAGE_ERROR,gtk.BUTTONS_CLOSE,msg)
		def close(dialog, response, editor):
			editor.about_dialog = None
			dialog.destroy()
		error_dialog.connect("response", close, self)
		self.error_dialog = error_dialog
		error_dialog.run()

	def on_loginbutton_clicked(self, data=None):
		self.wTree.get_object("login_dialog").response(gtk.RESPONSE_OK)

	def on_dial_clicked(self, widget):
		self.attemptLogin(3)

		if not self.gcd.isAuthed() or self.gcd.getCallbackNumber() == "":
			self.ErrPopUp("Backend link with grandcentral is not working, please try again")
			return

		#if len(self.phonenumber) == 7:
		#	#add default area code
		#	self.phonenumber = self.areacode + self.phonenumber
			
		if self.gcd.dial(self.phonenumber) == False: 
			self.ErrPopUp(self.gcd._msg)
		else:
			self.setNumber("")

		self.recentmodel.clear()
		self.recenttime = 0.0
		self.reduce_memory()

	def setNumber(self, number):
		self.phonenumber = makeugly(number)
		self.prettynumber = makepretty(self.phonenumber)
		self.numberdisplay.set_label("<span size='30000' weight='bold'>%s</span>" % ( self.prettynumber ) )

	def setAccountNumber(self):
		accountnumber = self.gcd.getAccountNumber()
		self.wTree.get_object("gcnumberlabel").set_label("<span size='23000' weight='bold'>%s</span>" % (accountnumber))

	def Backspace(self, widget):
		self.setNumber(self.phonenumber[:-1])

	def on_digit_clicked(self, widget):
		self.setNumber(self.phonenumber + re.sub('\D','',widget.get_label()))

if __name__ == "__main__":
	gc.set_threshold(50,3,3)
	title = 'Dialpad'
	handle = Dialpad()
	gtk.main()
	sys.exit(1)
