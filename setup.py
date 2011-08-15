#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
reload(sys).setdefaultencoding("UTF-8")
import os

try:
	from sdist_maemo import sdist_maemo as _sdist_maemo
	sdist_maemo = _sdist_maemo
except ImportError:
	sdist_maemo = None
	print 'sdist_maemo command not available'

from distutils.core import setup


#[[[cog
#	import cog
#	from dialcentral import constants
#	cog.outl('APP_NAME="%s"' % constants.__app_name__)
#	cog.outl('PRETTY_APP_NAME="%s"' % constants.__pretty_app_name__)
#	cog.outl('VERSION="%s"' % constants.__version__)
#	cog.outl('BUILD="%s"' % constants.__build__)
#	cog.outl('DESKTOP_FILE_PATH="%s"' % DESKTOP_FILE_PATH)
#	cog.outl('INPUT_DESKTOP_FILE="%s"' % INPUT_DESKTOP_FILE)
#	cog.outl('ICON_CATEGORY="%s"' % ICON_CATEGORY)
#	cog.outl('ICON_SIZES=[%s]' % ICON_SIZES)
#]]]
APP_NAME="dialcentral"
PRETTY_APP_NAME="DialCentral"
VERSION="1.3.6"
BUILD="0"
DESKTOP_FILE_PATH="/usr/share/applications"
INPUT_DESKTOP_FILE="data/ubuntu/dialcentral.desktop"
ICON_CATEGORY="apps"
ICON_SIZES=[32,48]
#[[[end]]] (checksum: 6b362845c8509854ec12f330afd9c7b7)

CHANGES = """* Fixing a launch issue with previous python versions
""".strip()
BUGTRACKER_URL = "https://bugs.maemo.org/enter_bug.cgi?product=Dialcentral"


def is_package(path):
	return (
		os.path.isdir(path) and
		os.path.isfile(os.path.join(path, '__init__.py'))
	)


def find_packages(path, base="", includeRoot=False):
	""" Find all packages in path """
	if includeRoot:
		assert not base, "Base not supported with includeRoot: %r" % base
		rootPath, module_name = os.path.split(path)
		yield module_name
		base = module_name
	for item in os.listdir(path):
		dir = os.path.join(path, item)
		if is_package( dir ):
			if base:
				module_name = "%(base)s.%(item)s" % vars()
			else:
				module_name = item
			yield module_name
			for mname in find_packages(dir, module_name):
				yield mname


setup(
	name=APP_NAME,
	version=VERSION,
	description="Touch screen enhanced interface to the GoogleVoice phone service",
	long_description="Touch screen enhanced interface to the GoogleVoice phone service",
	author="Ed Page",
	author_email="eopage@byu.net",
	maintainer="Ed Page",
	maintainer_email="eopage@byu.net",
	url="http://wiki.maemo.org/DialCentral",
	license="GNU LGPLv2.1",
	scripts=[
		"DialCentral",
	],
	packages=list(find_packages(APP_NAME, includeRoot=True)),
	package_data={
		"dialcentral": ["data/*.wav", "data/*.png"],
	},
	data_files=[
		(DESKTOP_FILE_PATH, [INPUT_DESKTOP_FILE]),
		("/usr/share/icons/hicolor/scalable/apps", ["data/%s.svg" % APP_NAME]),
	] +
	[
		(
			"/usr/share/icons/hicolor/%sx%s/%s" % (size, size, ICON_CATEGORY),
			["data/icons/%s/%s.png" % (size, APP_NAME)]
		)
		for size in ICON_SIZES
	],
	requires=[
		"PySide",
		"xml",
	],
	cmdclass={
		'sdist_ubuntu': sdist_maemo,
		'sdist_diablo': sdist_maemo,
		'sdist_fremantle': sdist_maemo,
		'sdist_harmattan': sdist_maemo,
	},
	options={
		"sdist_ubuntu": {
			"debian_package": APP_NAME,
			"section": "comm",
			"copyright": "lgpl",
			"changelog": CHANGES,
			"buildversion": str(BUILD),
			"depends": "python, python-pyside.qtcore, python-pyside.qtgui, python-xdg, python-dbus, python-gst0.10",
			"architecture": "any",
		},
		"sdist_diablo": {
			"debian_package": APP_NAME,
			"Maemo_Display_Name": PRETTY_APP_NAME,
			#"Maemo_Upgrade_Description": CHANGES,
			"Maemo_Bugtracker": BUGTRACKER_URL,
			"Maemo_Icon_26": "data/icons/26/%s.png" % APP_NAME,
			"section": "user/network",
			"copyright": "lgpl",
			"changelog": CHANGES,
			"buildversion": str(BUILD),
			"depends": "python2.5, python2.5-qt4-core, python2.5-qt4-gui, python-xdg, python-simplejson, python-xml | python2.5-xml, python-dbus | python2.5-dbus",
			"architecture": "any",
		},
		"sdist_fremantle": {
			"debian_package": APP_NAME,
			"Maemo_Display_Name": PRETTY_APP_NAME,
			#"Maemo_Upgrade_Description": CHANGES,
			"Maemo_Bugtracker": BUGTRACKER_URL,
			"Maemo_Icon_26": "data/icons/48/%s.png" % APP_NAME,
			"section": "user/network",
			"copyright": "lgpl",
			"changelog": CHANGES,
			"buildversion": str(BUILD),
			"depends": "python2.5, python2.5-qt4-core, python2.5-qt4-gui, python2.5-qt4-maemo5, python-xdg, python-simplejson, python-xml | python2.5-xml, python-dbus | python2.5-dbus",
			#"depends": "python, python-pyside.qtcore, python-pyside.qtgui, python-pyside.qtmaemo5, python-xdg, python-simplejson, python-gst0.10, python-xml | python2.5-xml, python-dbus | python2.5-dbus",
			"architecture": "any",
		},
		"sdist_harmattan": {
			"debian_package": APP_NAME,
			"Maemo_Display_Name": PRETTY_APP_NAME,
			#"Maemo_Upgrade_Description": CHANGES,
			"Maemo_Bugtracker": BUGTRACKER_URL,
			"Maemo_Icon_26": "data/icons/48/%s.png" % APP_NAME,
			"MeeGo_Desktop_Entry_Filename": APP_NAME,
			#"MeeGo_Desktop_Entry": "",
			"section": "user/science",
			"copyright": "lgpl",
			"changelog": CHANGES,
			"buildversion": str(BUILD),
			"depends": "python, python-pyside.qtcore, python-pyside.qtgui, python-xdg",
			"architecture": "any",
		},
		"bdist_rpm": {
			"requires": "REPLACEME",
			"icon": "data/icons/48/%s.png" % APP_NAME,
			"group": "REPLACEME",
		},
	},
)
