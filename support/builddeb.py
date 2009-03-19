#!/usr/bin/python2.5

from py2deb import *


__appname__ = "dialcentral"
__description__ = "Simple interface to Google's GrandCentral(tm) service"
__author__ = "Ed Page"
__email__ = "eopage@byu.net"
__version__ = "0.9.1"
__build__ = 0
__changelog__ = '''\
0.9.1 - "Get your hands off that"
 * GoogleVoice Support, what a pain
 * More flexible CSV support.  It now checks the header row for what column name/number are in
 * Experimenting with faster startup by caching PYC files with the package

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


__postinstall__ = '''#!/bin/sh

gtk-update-icon-cache /usr/share/icons/hicolor
'''


if __name__ == "__main__":
	try:
		os.chdir(os.path.dirname(sys.argv[0]))
	except:
		pass

	p = Py2deb(__appname__)
	p.description = __description__
	p.author = __author__
	p.mail = __email__
	p.license = "lgpl"
	p.depends = "python2.5, python2.5-gtk2"
	# p.section = "user/utilities"
	p.section = "user/communication"
	p.arch = "all"
	p.urgency = "low"
	p.distribution = "chinook diablo"
	p.repository = "extras-devel"
	p.changelog = __changelog__
	p.postinstall = __postinstall__
	p.icon="26x26-dialcentral.png"
	p["/usr/bin"] = [ "dialcentral.py" ]
	p["/usr/lib/dialcentral"] = [
		"dialcentral.glade",
		"__init__.py",
		"dialer.py",
		"browser_emu.py",
		"file_backend.py",
		"evo_backend.py",
		"gc_backend.py",
		"gv_backend.py",
		"gc_views.py",
		"null_views.py",
		"gtk_toolbox.py",
		"__init__.pyc",
		"dialer.pyc",
		"browser_emu.pyc",
		"file_backend.pyc",
		"evo_backend.pyc",
		"gc_backend.pyc",
		"gv_backend.pyc",
		"gc_views.pyc",
		"null_views.pyc",
		"gtk_toolbox.pyc",
	]
	p["/usr/share/applications/hildon"] = ["dialcentral.desktop"]
	p["/usr/share/icons/hicolor/26x26/hildon"] = ["26x26-dialcentral.png|dialcentral.png"]
	p["/usr/share/icons/hicolor/64x64/hildon"] = ["64x64-dialcentral.png|dialcentral.png"]
	p["/usr/share/icons/hicolor/scalable/hildon"] = ["scale-dialcentral.png|dialcentral.png"]

	print p
	print p.generate(
		__version__, __build__, changelog=__changelog__,
		tar=True, dsc=True, changes=True, build=False, src=True
	)
