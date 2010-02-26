#!/usr/bin/python2.5

import os
import sys

try:
	import py2deb
except ImportError:
	import fake_py2deb as py2deb

import constants


__appname__ = constants.__app_name__
__description__ = """Touch screen enhanced interface to the GoogleVoice phone service"
Features:
.
* Dialpad for quick call
.
* Checking voicemails, texts, call history
.
* Sending texts
.
* Notification support for texts, voicemail, and/or missed calls
.
Homepage: http://gc-dialer.garage.maemo.org/
"""
__author__ = "Ed Page"
__email__ = "eopage@byu.net"
__version__ = constants.__version__
__build__ = constants.__build__
__changelog__ = """
1.1.7
* Adjusting how numbers are normalized
1.1.6
* Added back in separate call/sms buttons
1.1.5
* Bugfix from 1.1.2: Was not displaying errors in SMS window
1.1.4
* Bugfix from 1.1.0: Scroll to bottom when removing a recipient
* Bugfix from 1.1.3: Maemo 5 fix was incomplete
1.1.3
* Broadcast SMS: Increased the spacing between contacts
* SMS: Added Ctrl+h shortcut to hide the window for adding more recipients to the SMS
* Bugfix from 1.1.0: In "Messages" if "Texts" was selected, you saw nothing
* Bugfix from 1.1.0: Issues with SMS window on Maemo
* Bugfix from 1.1.0: Maemo 5 SMS dialog is not working
1.1.2
* Broadcast SMS: Added names to the rows
* Broadcast SMS: Disabled changing number when there weren't numbers to change to
* SMS: Reformatted the SMS window a tad
* SMS: Added a proper non-modal error box to the SMS window
* Bugfix from 1.1.0: hildonizing the SMS Entry Window
* Bugfix from 1.1.0: Race condition in creating SMS Entry Window
1.1.1
* SMS: Added icons to the SMS window buttons
* SMS: When selecting a number in the history tab, the call history is now shown in the SMS window
* Bugfix from 1.1.0: "Letters Left:" is now "Letters:"
* Bugfix from 1.1.0: When looking for alt numbers, there were issues
1.1.0
* Dialpad: Support for "+" in numbers, including on Dialpad by holding "0".  I'm hoping this makes both international and Gizmo users happier
* SMS: Added support for multi-part SMS messages (just like the GV site)
* SMS: Switching the sms entry dialog to a window with some key combos
* Broadcast SMS: Added it
* Contacts: Unofficial support for importing of contacts files through Ctrl+i
* Bugfixes carried over from TOR work

1.0.10
* Renamed Recent to History
* Sped up GV contacts
* Remember if fullscreen (Ctrl+enter) in settings
* Added Ctrl+w and Ctrl+q to quit
* Added a filter for the Call History
* Error logging for notifications
* Bugfix: Messages tab not showing all of a message in Fremantle
* Bugfix: When selecting a message, the wrong message is displayed in the Send SMS dialog
* Bugfix: Removing some false positives for notification

1.0.9
* Added .deb packages for generic linux
* UI Tweak: Added an app menu
* Bug Fix: "Unable to Complete Calls Out" due to google.com/voice/m issues

1.0.8
* Sped up login time by delay loading contact list
* Sped up login when you do not have a cookie file (first launch)
* Ability to narrow down messages either by type or status
* Fremantle: Notification Support including testing of custom notifications
* UI Tweak: Cut down the number of times the login dialog is needlessly displayed
* Bug Fix: Switching to accounts tab when callback is blank
* Bug Fix: Corrupt cookie files prevent login
* Bug Fix: Logging in without credentials through cookies
* Debugging: Log contents now accessible through Ctrl+l

1.0.7
* Sped up various login cases
* Added descriptions to the callback numbers
* Collapsed conversations in the messages tab
* Give access to all of a contacts numbers when launching dialog from Recent or Messages tabs
* UI Tweak: Added more login status notifications
* UI Tweak: When no characters are entered, you can't send a text
* UI Tweak: Trying to consolidate dialogs by combining phone selection and SMS entry
* UI Tweak: Removed "Select" button from SMS Dialog
* UI Tweak: Increased the size of the SMS dialog
* UI Tweak: Disable "Dial" when a text has started to be entered
* UI Tweak: Move the sms history scroll bars around the whole sms conversation, giving more room to see with
* UI Tweak: Trying to be clearer by switching the login dialog from "Close" to "Cancel"
* UI Tweak: Remove auto-cancel of login after X attempts
* Bug Fix: Expanded the types of the Enter key that are supported for going to full screen
* Bug Fix: Random people were reporting login issues
* Bug Fix: Hardened against issues with grabbing possible callback numbers
* Bug Fix: Fremantle GTK doesn't allow TreeView rows to be selected, so row-activated handlers have to read their path
* Bug Fix: Fremantle PyMaemo doesn't provide a function Mer PyMaemo does, created a hack to be workable on both
* Bug Fix: Once PyMaemo supports thumb button sizes, setting that for all of the random buttons
* Bug Fix: When debugging hildonization, dialogs weren't closing
* Bug Fix: Not properly hildonizing some code
* Bug Fix: Attempting a hack to fix redirect issues for people
* Debugging: Improved logging output
* Debugging: Printing page when can't get a callback number
* Debugging: Included stuff to create all the debug files

1.0.6
* Fremantle Prep: Simplified menus in prep for no menu or the Fremantle App Menu
* Fremantle Prep: Implemented a work around for https://bugs.maemo.org/show_bug.cgi?id=4957
* Fremantle Prep: Switched to touch selectors for notification time, callback number, and contact addressbook
* Fremantle Prep: Making various widgets pannable rather than scrollable
* Fremantle Prep: CTRL-V added for paste for Dialpad
* Fremantle Prep: CTRL-Enter added for fullscreen
* UI Tweak: Phone selection and SMS Message dialogs now highlight the last message and are easier to scroll
* UI Tweak: Tweaked sizes of stuff on recent tab
* UI Tweak: Added notifcations for various things like login and dialing
* UI Tweak: Switch to accounts tab when logging in and callback is blank as a sublte hint to configure it
* UI Tweak: Switch to accounts tab on failed login to remind the user they are not logged in
* Packaging: Disables notifications on uninstall
* Packaging: Including a vastly improved py2deb for better packages (icons on package, etc)
* Debugging: Adding seperator between dialcentral launches in log
* Bug Fix: Made startup more error resistant
* Bug Fix: some dependencies for Diablo
* Bug Fix: Error on refreshing tabs when not logged in
* Bug Fix: #4471 Notification Checkbox Won't Stay Checked (hour roll over error)
* Bug Fix: Phone numbers in voicemails wouldn't appear
* Bug Fix: category for Fremantle/Diablo
* Bug Fix: needing to manually create "~/.dialcentral" due to earlier logging changes
* Bug Fix: dependencies for fremantle
* Bug Fix: Issues when trying to stack error messages
* Bug Fix: Python2.6 deprecates some stuff I did
* Bug Fix: On refreshing the Accounts tab, the callback number resets to the number from startup

1.0.5
* Contacts Tab remembers the last address book viewed on restart
* Applied some suggested changes for being more thumb friendly
* Messaging Dialog auto-scrolls to bottom
* Removed GrandCentral support
* Numbers can now be entered immediately, before login
* Bug Fix: Not clearing the entered number on sending an SMS
* Bug Fix: Disabling SMS button when logged off
* Bug Fix: Trying to make SMS and phone selection dialogs more readable
* Bug Fix: Adding some more thumb scrollbars

1.0.4
* "Back" button and tabs now visually indicate when they've entered a "hold" state
* Fixed the duplicate title on Maemo
* Removing some device connection observer code due to high bug to low benefit ratio
* Notification support
* Fixed a bug from 1.0.3 where once you refreshed a tab by holding on it, every tab would then be forced to refresh

1.0.3
* Holding down a tab for a second will now force a refresh
* Fixed a bug dealing with overzealously refreshing the contacts tab
* Finding some undescriptive errors and made them more descriptive
* Swapped the order GrandCentral and GoogleVoice appear in login window
* Fixed the "Recent" and "Message" tabs, google changed things on me again

1.0.2
* Random bug fixes
* Random performance improvements

1.0.1
* Fixed a voicemail transcripts due to a GoogleVoice change

1.0.0
* Added names to the recent tab for GoogleVoice

0.9.9
* SMS From Dialpad
* Display of names for messages tab
* Condensed messages/recent's date column

0.9.8
 * Added columns to recent view and messages view to help seperate messages
 * Attempted refreshing session on dial/sms send
 * Fixed a GC Bug
 * Minor bug fixes as usual

0.9.7
 * Switched to Force Refresh for when wanting to check for more messages
 * Removed timeouts that forced refreshes on various tabs
 * Added support for a settings file, fairly primitive right now
 * Fixed Maemo Support
 * Lots of major and minor bug fixes

0.9.6
 * Experimenting with the tabs being on the side
 * Now the phone selector is used always, even if there is just one phone number
 * Added a Messages Tab, which displays SMS and Voicemail messages
 * Added option to send SMS messages

0.9.5
 * Fixed a login issue due to Google changing their webpage

0.9.4 - ""
 * Misc Bug fixes and experiments

0.9.3 - ""
 * Removed the much disliked contact source ID
 * Added saving of callback number when using GoogleVoice
 * Got proper formatting on things ("&" rather than "&amp;")
 * Misc Bug fixes

0.9.2 - "Two heads are better than one"
 * Adding of UI to switch between GC and GV
 * Minimized flashing the dial button between grayed out and not on startup
 * Bug fixes

0.9.1 - "Get your hands off that"
 * GoogleVoice Support, what a pain
 * More flexible CSV support.  It now checks the header row for what column name/number are in
 * Experimenting with faster startup by caching PYC files with the package
 * Fixing of some bad error handling
 * More debug output for when people run into issues

0.9.0 - "Slick as snot"
 * Caching of contacts
 * Refactoring to make working with the code easier
 * Filesystem backed contacts but currently only supporting a specific csv format
 * Gracefully handle lack of connection and connection transitions
 * Gracefully handle failed login
 * A tiny bit better error reporting

0.8.3 - "Extras Love"
 * Version bump fighting the extras autobuilder, I hope this works

0.8.2 - "Feed is for horses, so what about feedback?"
 * Merged addressbook
 * many more smaller fixes

0.8.1 - "Two Beers"
 * Thumb scrollbars ( Kudos Khertan )

0.8.0 - "Spit and polish"
 * Addressbook support
 * threaded networking for better interactivity
 * Hold down back to clear number
 * Standard about dialog
 * many more smaller fixes
"""


__postinstall__ = """#!/bin/sh -e

gtk-update-icon-cache -f /usr/share/icons/hicolor
rm -f ~/.dialcentral/notifier.log
rm -f ~/.dialcentral/dialcentral.log
"""

__preremove__ = """#!/bin/sh -e

python /usr/lib/dialcentral/alarm_handler.py -d || true
"""


def find_files(path):
	for root, dirs, files in os.walk(path):
		for file in files:
			if file.startswith("src-"):
				fileParts = file.split("-")
				unused, relPathParts, newName = fileParts[0], fileParts[1:-1], fileParts[-1]
				assert unused == "src"
				relPath = os.sep.join(relPathParts)
				yield relPath, file, newName


def unflatten_files(files):
	d = {}
	for relPath, oldName, newName in files:
		if relPath not in d:
			d[relPath] = []
		d[relPath].append((oldName, newName))
	return d


def build_package(distribution):
	try:
		os.chdir(os.path.dirname(sys.argv[0]))
	except:
		pass

	py2deb.Py2deb.SECTIONS = py2deb.SECTIONS_BY_POLICY[distribution]
	p = py2deb.Py2deb(__appname__)
	p.prettyName = constants.__pretty_app_name__
	p.description = __description__
	p.bugTracker = "https://bugs.maemo.org/enter_bug.cgi?product=Dialcentral"
	p.upgradeDescription = __changelog__.split("\n\n", 1)[0]
	p.author = __author__
	p.mail = __email__
	p.license = "lgpl"
	p.depends = ", ".join([
		"python2.6 | python2.5",
		"python-gtk2 | python2.5-gtk2",
		"python-xml | python2.5-xml",
		"python-dbus | python2.5-dbus",
	])
	maemoSpecificDepends = ", python-osso | python2.5-osso, python-hildon | python2.5-hildon"
	p.depends += {
		"debian": ", python-glade2",
		"diablo": maemoSpecificDepends + ", python2.5-conic",
		"fremantle": maemoSpecificDepends + ", python-glade2, python-alarm",
		"mer": maemoSpecificDepends + ", python-glade2",
	}[distribution]
	p.recommends = ", ".join([
	])
	p.section = {
		"debian": "comm",
		"diablo": "user/network",
		"fremantle": "user/network",
		"mer": "user/network",
	}[distribution]
	p.arch = "all"
	p.urgency = "low"
	p.distribution = "diablo fremantle mer debian"
	p.repository = "extras"
	p.changelog = __changelog__
	p.postinstall = __postinstall__
	p.preremove = __preremove__
	p.icon = {
		"debian": "26x26-dialcentral.png",
		"diablo": "26x26-dialcentral.png",
		"fremantle": "64x64-dialcentral.png", # Fremantle natively uses 48x48
		"mer": "64x64-dialcentral.png",
	}[distribution]
	p["/usr/bin"] = [ "dialcentral.py" ]
	for relPath, files in unflatten_files(find_files(".")).iteritems():
		fullPath = "/usr/lib/dialcentral"
		if relPath:
			fullPath += os.sep+relPath
		p[fullPath] = list(
			"|".join((oldName, newName))
			for (oldName, newName) in files
		)
	p["/usr/share/applications/hildon"] = ["dialcentral.desktop"]
	p["/usr/share/icons/hicolor/26x26/hildon"] = ["26x26-dialcentral.png|dialcentral.png"]
	p["/usr/share/icons/hicolor/64x64/hildon"] = ["64x64-dialcentral.png|dialcentral.png"]
	p["/usr/share/icons/hicolor/scalable/hildon"] = ["scale-dialcentral.png|dialcentral.png"]

	if distribution == "debian":
		print p
		print p.generate(
			version="%s-%s" % (__version__, __build__),
			changelog=__changelog__,
			build=True,
			tar=False,
			changes=False,
			dsc=False,
		)
		print "Building for %s finished" % distribution
	else:
		print p
		print p.generate(
			version="%s-%s" % (__version__, __build__),
			changelog=__changelog__,
			build=False,
			tar=True,
			changes=True,
			dsc=True,
		)
		print "Building for %s finished" % distribution


if __name__ == "__main__":
	if len(sys.argv) > 1:
		try:
			import optparse
		except ImportError:
			optparse = None

		if optparse is not None:
			parser = optparse.OptionParser()
			(commandOptions, commandArgs) = parser.parse_args()
	else:
		commandArgs = None
		commandArgs = ["diablo"]
	build_package(commandArgs[0])
