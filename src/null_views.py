#!/usr/bin/python2.5

"""
DialCentral - Front end for Google's Grand Central service.
Copyright (C) 2008  Mark Bergman bergman AT merctech DOT com

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
"""

import gobject
import gtk


class Dialpad(object):

	def __init__(self, widgetTree):
		self._numberdisplay = widgetTree.get_widget("numberdisplay")
		self._dialButton = widgetTree.get_widget("dial")

	def enable(self):
		self._dialButton.set_sensitive(False)

	def disable(self):
		self._dialButton.set_sensitive(True)


class AccountInfo(object):

	def __init__(self, widgetTree):
		self._callbackList = gtk.ListStore(gobject.TYPE_STRING)
		self._accountViewNumberDisplay = widgetTree.get_widget("gcnumber_display")
		self._callbackCombo = widgetTree.get_widget("callbackcombo")
		self._clearCookiesButton = widgetTree.get_widget("clearcookies")

	def enable(self):
		self._callbackCombo.set_sensitive(False)
		self._clearCookiesButton.set_sensitive(False)

		self._accountViewNumberDisplay.set_text("")

	def disable(self):
		self._clearCookiesButton.set_sensitive(True)
		self._callbackCombo.set_sensitive(True)

	@staticmethod
	def update():
		pass

	@staticmethod
	def clear():
		pass


class RecentCallsView(object):

	def __init__(self, widgetTree):
		pass

	def enable(self):
		pass

	def disable(self):
		pass

	def update(self):
		pass

	@staticmethod
	def clear():
		pass


class ContactsView(object):

	def __init__(self, widgetTree):
		self._booksSelectionBox = widgetTree.get_widget("addressbook_combo")

	def enable(self):
		self._booksSelectionBox.set_sensitive(False)

	def disable(self):
		self._booksSelectionBox.set_sensitive(True)

	def update(self):
		pass

	@staticmethod
	def clear():
		pass
