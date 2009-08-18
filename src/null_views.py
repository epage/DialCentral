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

	@staticmethod
	def name():
		return "Dialpad"

	def load_settings(self, config, sectionName):
		pass

	def save_settings(self, config, sectionName):
		"""
		@note Thread Agnostic
		"""
		pass


class AccountInfo(object):

	def __init__(self, widgetTree):
		self._callbackList = gtk.ListStore(gobject.TYPE_STRING)
		self._accountViewNumberDisplay = widgetTree.get_widget("gcnumber_display")
		self._callbackCombo = widgetTree.get_widget("callbackcombo")
		self._clearCookiesButton = widgetTree.get_widget("clearcookies")

		self._notifyCheckbox = widgetTree.get_widget("notifyCheckbox")
		self._minutesEntry = widgetTree.get_widget("minutesEntry")
		self._missedCheckbox = widgetTree.get_widget("missedCheckbox")
		self._voicemailCheckbox = widgetTree.get_widget("voicemailCheckbox")
		self._smsCheckbox = widgetTree.get_widget("smsCheckbox")

	def enable(self):
		self._callbackCombo.set_sensitive(False)
		self._clearCookiesButton.set_sensitive(False)

		self._notifyCheckbox.set_sensitive(False)
		self._minutesEntry.set_sensitive(False)
		self._missedCheckbox.set_sensitive(False)
		self._voicemailCheckbox.set_sensitive(False)
		self._smsCheckbox.set_sensitive(False)

		self._accountViewNumberDisplay.set_label("")

	def disable(self):
		self._callbackCombo.set_sensitive(True)
		self._clearCookiesButton.set_sensitive(True)

		self._notifyCheckbox.set_sensitive(True)
		self._minutesEntry.set_sensitive(True)
		self._missedCheckbox.set_sensitive(True)
		self._voicemailCheckbox.set_sensitive(True)
		self._smsCheckbox.set_sensitive(True)

	@staticmethod
	def update():
		return False

	@staticmethod
	def clear():
		pass

	@staticmethod
	def name():
		return "Account Info"

	def load_settings(self, config, sectionName):
		pass

	def save_settings(self, config, sectionName):
		"""
		@note Thread Agnostic
		"""
		pass


class RecentCallsView(object):

	def __init__(self, widgetTree):
		pass

	def enable(self):
		pass

	def disable(self):
		pass

	def update(self):
		return False

	@staticmethod
	def clear():
		pass

	@staticmethod
	def name():
		return "Recent Calls"

	def load_settings(self, config, sectionName):
		pass

	def save_settings(self, config, sectionName):
		"""
		@note Thread Agnostic
		"""
		pass


class MessagesView(object):

	def __init__(self, widgetTree):
		pass

	def enable(self):
		pass

	def disable(self):
		pass

	def update(self):
		return False

	@staticmethod
	def clear():
		pass

	@staticmethod
	def name():
		return "Messages"

	def load_settings(self, config, sectionName):
		pass

	def save_settings(self, config, sectionName):
		"""
		@note Thread Agnostic
		"""
		pass


class ContactsView(object):

	def __init__(self, widgetTree):
		self._booksSelectionBox = widgetTree.get_widget("addressbook_combo")

	def enable(self):
		self._booksSelectionBox.set_sensitive(False)

	def disable(self):
		self._booksSelectionBox.set_sensitive(True)

	def update(self):
		return False

	@staticmethod
	def clear():
		pass

	@staticmethod
	def name():
		return "Contacts"

	def load_settings(self, config, sectionName):
		pass

	def save_settings(self, config, sectionName):
		"""
		@note Thread Agnostic
		"""
		pass
