#!/usr/bin/python 

# Grandcentral Dialer
# Python front-end to a wget script to use grandcentral.com to place outbound VOIP calls.
# (C) 2008 Mark Bergman
# bergman@merctech.com

import sys
import os
import time
import re
try:
	import pygtk
	pygtk.require("2.0")
except:
	pass
try:
	import gtk
	import gtk.glade
except:
	sys.exit(1)

histfile=os.path.expanduser("~")
histfile=os.path.join(histfile,".gcdialerhist")	# Use the native OS file separator
liststore = gtk.ListStore(str)

class GCDialer:
	_wgetOKstrRe	= re.compile("This may take a few seconds", re.M)	# string from Grandcentral.com on successful dial 
	_validateRe	= re.compile("^[0-9]{7,}$")

	_wgetoutput	= "/tmp/gc_dialer.output"	# results from wget command
	_cookiefile	= os.path.join(os.path.expanduser("~"),".mozilla/microb/cookies.txt")	# file with browser cookies
	_wgetcmd	= "wget -nv -O %s --load-cookie=\"%s\" --referer=http://www.grandcentral.com/mobile/messages http://www.grandcentral.com/mobile/calls/click_to_call?destno=%s"

	def __init__(self):
		self._msg = ""
		if ( os.path.isfile(GCDialer._cookiefile) == False ) :
			self._msg = 'Error: Failed to locate a file with saved browser cookies at \"' + cookiefile + '\".\n\tPlease use the web browser on your tablet to connect to www.grandcentral.com and then re-run Grandcentral Dialer.'

	def validate(self,number):
		return GCDialer._validateRe.match(number) != None

	def dial(self,number):
		self._msg = ""
		if self.validate(number) == False:
			self._msg = "Invalid number format %s" % (number)
			return False

		# Remove any existing output file...
		if os.path.isfile(GCDialer._wgetoutput) :
			os.unlink(GCDialer._wgetoutput)
		child_stdout, child_stdin, child_stderr = os.popen3(GCDialer._wgetcmd % (GCDialer._wgetoutput, GCDialer._cookiefile, number))
		stderr=child_stderr.read()

		child_stdout.close()
		child_stderr.close()
		child_stdin.close()

		try:
			wgetresults = open(GCDialer._wgetoutput, 'r' )
		except IOError:
			self._msg = 'IOError: No /tmp/gc_dialer.output file...dial attempt failed\n\tThis probably means that there is no active internet connection, or that\nthe site www.grandcentral.com is inacessible.'
			return False
		
		data = wgetresults.read()
		wgetresults.close()

		if GCDialer._wgetOKstrRe.search(data) != None:
			return True
		else:
			self._msg = 'Error: Failed to login to www.grandcentral.com.\n\tThis probably means that there is no saved cookie for that site.\n\tPlease use the web browser on your tablet to connect to www.grandcentral.com and then re-run Grandcentral Dialer.'
			return False


def load_history_list(histfile,liststore):
	# read the history list, load it into the liststore variable for later
	# assignment to the combobox menu

	# clear out existing entries
	dialhist = []
	liststore.clear()
	if os.path.isfile(histfile) :
		histFH = open(histfile,"r")
		for line in histFH.readlines() :
			fields = line.split()	# split the input lines on whitespace
			number=fields[0]		#...save only the first field (the phone number)
			search4num=re.compile('^' + number + '$')
			newnumber=True	# set a flag that the current phone number is not on the history menu
			for num in dialhist :
				if re.match(search4num,num):
					# the number is already in the drop-down menu list...set the
					# flag and bail out
					newnumber = False
					break
			if newnumber == True :
				dialhist.append(number)	# append the number to the history list
	
		histlen=len(dialhist)
		if histlen > 10 :
			dialhist=dialhist[histlen - 10:histlen]		# keep only the last 10 entries
		dialhist.reverse()	# reverse the list, so that the most recent entry is now first
	
		# Now, load the liststore with the entries, for later assignment to the Gtk.combobox menu
		for entry in dialhist :
			entry=makepretty(entry)
			liststore.append([entry])
	# else :
	#	 print "The history file " + histfile + " does not exist"

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
	elif len(phonenumber) <= 7 :
			prettynumber = phonenumber[0:3] + "-" + phonenumber[3:] 
	elif len(phonenumber) > 7 :
			prettynumber = "(" + phonenumber[0:3] + ")-" + phonenumber[3:6] + "-" + phonenumber[6:]
	return prettynumber

class Dialpad:

	phonenumber = ""

	def __init__(self):
		if os.path.isfile("/usr/local/lib/gc_dialer.glade") :
			self.gladefile = "/usr/local/lib/gc_dialer.glade"  
		elif os.path.isfile("./gc_dialer.glade") :
			self.gladefile = "./gc_dialer.glade"

		self.gcd = GCDialer()
		if self.gcd._msg != "":
			self.ErrPopUp(self.gcd._msg)
			sys.exit(1)

		self.wTree = gtk.glade.XML(self.gladefile)
		self.window = self.wTree.get_widget("Dialpad")
		if (self.window):
			self.window.connect("destroy", gtk.main_quit)
		#Get the buffer associated with the number display
		self.numberdisplay = self.wTree.get_widget("numberdisplay")
		self.dialer_history = self.wTree.get_widget("dialer_history")

		# Load the liststore array with the numbers from the history file
		load_history_list(histfile,liststore)
		# load the dropdown menu with the numbers from the dial history
		self.dialer_history.set_model(liststore)
		cell = gtk.CellRendererText()
		self.dialer_history.pack_start(cell, True)
		self.dialer_history.set_active(-1)
		self.dialer_history.set_attributes(cell, text=0)

		self.about_dialog = None
		self.error_dialog = None

		dic = {
			# Routine for processing signal from the combobox (ie., when the
			# user selects an entry from the dropdown history
		 	"on_dialer_history_changed" : self.on_dialer_history_changed,

			# Process signals from buttons
			"on_number_clicked"  : self.on_number_clicked,
			"on_Clear_clicked"   : self.on_Clear_clicked,
			"on_Dial_clicked"    : self.on_Dial_clicked,
			"on_Backspace_clicked" : self.Backspace,
			"on_Cancel_clicked"  : self.on_Cancel_clicked,
			"on_About_clicked"   : self.on_About_clicked}
		self.wTree.signal_autoconnect(dic)

	def ErrPopUp(self,msg):
		error_dialog = gtk.MessageDialog(None,0,gtk.MESSAGE_ERROR,gtk.BUTTONS_CLOSE,msg)
		def close(dialog, response, editor):
			editor.about_dialog = None
			dialog.destroy()
		error_dialog.connect("response", close, self)
		# error_dialog.connect("delete-event", delete_event, self)
		self.error_dialog = error_dialog
		error_dialog.run()

	def on_About_clicked(self, menuitem, data=None):
		if self.about_dialog: 
			self.about_dialog.present()
			return

		authors = [ "Mark Bergman <bergman@merctech.com>",
				"Eric Warnke <ericew@gmail.com>" ]

		about_dialog = gtk.AboutDialog()
		about_dialog.set_transient_for(None)
		about_dialog.set_destroy_with_parent(True)
		about_dialog.set_name("Grandcentral Dialer")
		about_dialog.set_version("0.5")
		about_dialog.set_copyright("Copyright \xc2\xa9 2008 Mark Bergman")
		about_dialog.set_comments("GUI front-end to initiate outbound call from Grandcentral.com, typically with Grancentral configured to connect the outbound call to a VOIP number accessible via Gizmo on the Internet Tablet.\n\nRequires an existing browser cookie from a previous login session to http://www.grandcentral.com/mobile/messages and the program 'wget'.")
		about_dialog.set_authors            (authors)
		about_dialog.set_logo_icon_name     (gtk.STOCK_EDIT)

		# callbacks for destroying the dialog
		def close(dialog, response, editor):
			editor.about_dialog = None
			dialog.destroy()

		def delete_event(dialog, event, editor):
			editor.about_dialog = None
			return True

		about_dialog.connect("response", close, self)
		about_dialog.connect("delete-event", delete_event, self)
		self.about_dialog = about_dialog
		about_dialog.show()

	def on_Dial_clicked(self, widget):
		# Strip the leading "1" before the area code, if present
		if len(Dialpad.phonenumber) == 11 and Dialpad.phonenumber[0] == "1" :
				Dialpad.phonenumber = Dialpad.phonenumber[1:]
		prettynumber = makepretty(Dialpad.phonenumber)
		if len(Dialpad.phonenumber) < 7 :
			# It's too short to be a phone number
			msg = 'Phone number "%s" is too short' % ( prettynumber )
			self.ErrPopUp(msg)
		else :
			timestamp=time.asctime(time.localtime())
			
			if self.gcd.dial(Dialpad.phonenumber) == True : 
				histFH = open(histfile,"a")
				histFH.write("%s dialed at %s\n" % ( Dialpad.phonenumber, timestamp ) )
				histFH.close()

				# Re-load the updated history of dialed numbers
				load_history_list(histfile,liststore)
				self.dialer_history.set_active(-1)
				self.on_Clear_clicked(widget)
			else:
				self.ErrPopUp(self.gcd._msg)

	def on_Cancel_clicked(self, widget):
		sys.exit(1)

	def Backspace(self, widget):
		Dialpad.phonenumber = Dialpad.phonenumber[:-1]
		prettynumber = makepretty(Dialpad.phonenumber)
		self.numberdisplay.set_text(prettynumber)

	def on_Clear_clicked(self, widget):
		Dialpad.phonenumber = ""
		self.numberdisplay.set_text(Dialpad.phonenumber)

	def on_dialer_history_changed(self,widget):
		# Set the displayed number to the number chosen from the history list
		history_list = self.dialer_history.get_model()
		history_index = self.dialer_history.get_active()
		prettynumber = history_list[history_index][0]
		Dialpad.phonenumber = makeugly(prettynumber)
		self.numberdisplay.set_text(prettynumber)

	def on_number_clicked(self, widget):
		Dialpad.phonenumber = Dialpad.phonenumber + re.sub('\D','',widget.get_label())
		prettynumber = makepretty(Dialpad.phonenumber)
		self.numberdisplay.set_text(prettynumber)



if __name__ == "__main__":
	title = 'Dialpad'
	handle = Dialpad()
	gtk.main()
	sys.exit(1)
