#!/usr/bin/python2.5

from py2deb import *


__appname__ = "dialcentral"
__description__ = "Simple interface to Google's GrandCentral(tm) service"
__author__ = "Ed Page"
__email__ = "eopage@byu.net"
__version__ = "0.8.4"
__build__ = 0
__changelog__ = '''\
0.8.4 - ""

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
	p["/usr/lib/dialcentral"] = ["__init__.py", "browser_emu.py", "evo_backend.py", "gc_backend.py", "gc_dialer.glade", "gc_dialer.py", "builddeb.py"]
	p["/usr/share/applications/hildon"] = ["dialcentral.desktop"]
	p["/usr/share/icons/hicolor/26x26/hildon"] = ["26x26-dialcentral.png|dialcentral.png"]
	p["/usr/share/icons/hicolor/64x64/hildon"] = ["64x64-dialcentral.png|dialcentral.png"]
	p["/usr/share/icons/hicolor/scalable/hildon"] = ["scale-dialcentral.png|dialcentral.png"]

	print p
	print p.generate(
		__version__, __build__, changelog=__changelog__,
		tar=True, dsc=True, changes=True, build=False, src=True
	)
