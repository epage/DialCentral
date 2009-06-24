#!/usr/bin/python2.5

import os
import sys

try:
	import py2deb
except ImportError:
	import fake_py2deb as py2deb

import constants


__appname__ = constants.__app_name__
__description__ = "Touch screen enhanced interface to the GoogleVoice/GrandCentral phone service"
__author__ = "Ed Page"
__email__ = "eopage@byu.net"
__version__ = constants.__version__
__build__ = 0
__changelog__ = '''
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
'''


__postinstall__ = '''#!/bin/sh -e

gtk-update-icon-cache -f /usr/share/icons/hicolor
'''


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

	p = py2deb.Py2deb(__appname__)
	p.description = __description__
	p.author = __author__
	p.mail = __email__
	p.license = "lgpl"
	p.depends = {
		"diablo": "python2.5, python2.5-gtk2, python2.5-xml",
		"mer": "python2.6, python-gtk2, python-xml, python-glade2",
	}[distribution]
	p.section = "user/communication"
	p.arch = "all"
	p.urgency = "low"
	p.distribution = "chinook diablo fremantle mer"
	p.repository = "extras"
	p.changelog = __changelog__
	p.postinstall = __postinstall__
	p.icon = "26x26-dialcentral.png"
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

	print p
	print p.generate(
		__version__, __build__, changelog=__changelog__,
		tar=True, dsc=True, changes=True, build=False, src=True
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
