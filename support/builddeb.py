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
* Fixing a bug where a failed login would cause problems
* Fixing a bug preventing failed logins to be reported to the user
* Adding some more detail to the log
""".strip()


__postinstall__ = """#!/bin/sh -e

gtk-update-icon-cache -f /usr/share/icons/hicolor
rm -f ~/.%(name)s/%(name)s.log
rm -f ~/.%(name)s/notifier.log
""" % {"name": constants.__app_name__}

__preremove__ = """#!/bin/sh -e

python /opt/dialcentral/lib/alarm_handler.py -d || true
"""


def find_files(prefix, path):
	for root, dirs, files in os.walk(path):
		for file in files:
			if file.startswith(prefix+"-"):
				fileParts = file.split("-")
				unused, relPathParts, newName = fileParts[0], fileParts[1:-1], fileParts[-1]
				assert unused == prefix
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
	}[distribution]
	p.recommends = ", ".join([
	])
	p.section = {
		"debian": "comm",
		"diablo": "user/network",
		"fremantle": "user/network",
	}[distribution]
	p.arch = "all"
	p.urgency = "low"
	p.distribution = "diablo fremantle debian"
	p.repository = "extras"
	p.changelog = __changelog__
	p.postinstall = __postinstall__
	p.preremove = __preremove__
	p.icon = {
		"debian": "26x26-dialcentral.png",
		"diablo": "26x26-dialcentral.png",
		"fremantle": "64x64-dialcentral.png", # Fremantle natively uses 48x48
	}[distribution]
	p["/opt/%s/bin" % __appname__] = [ "%s.py" % __appname__ ]
	for relPath, files in unflatten_files(find_files("src", ".")).iteritems():
		fullPath = "/opt/%s/lib" % __appname__
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
