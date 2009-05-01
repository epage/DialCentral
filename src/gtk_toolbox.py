#!/usr/bin/python

from __future__ import with_statement

import sys
import traceback
import functools
import contextlib
import warnings

import gobject
import gtk


@contextlib.contextmanager
def gtk_lock():
	gtk.gdk.threads_enter()
	try:
		yield
	finally:
		gtk.gdk.threads_leave()


def make_idler(func):
	"""
	Decorator that makes a generator-function into a function that will continue execution on next call
	"""
	a = []

	@functools.wraps(func)
	def decorated_func(*args, **kwds):
		if not a:
			a.append(func(*args, **kwds))
		try:
			a[0].next()
			return True
		except StopIteration:
			del a[:]
			return False

	return decorated_func


def asynchronous_gtk_message(original_func):
	"""
	@note Idea came from http://www.aclevername.com/articles/python-webgui/
	"""

	def execute(allArgs):
		args, kwargs = allArgs
		original_func(*args, **kwargs)

	@functools.wraps(original_func)
	def delayed_func(*args, **kwargs):
		gobject.idle_add(execute, (args, kwargs))

	return delayed_func


def synchronous_gtk_message(original_func):
	"""
	@note Idea came from http://www.aclevername.com/articles/python-webgui/
	"""

	@functools.wraps(original_func)
	def immediate_func(*args, **kwargs):
		with gtk_lock():
			return original_func(*args, **kwargs)

	return immediate_func


class LoginWindow(object):

	def __init__(self, widgetTree):
		"""
		@note Thread agnostic
		"""
		self._dialog = widgetTree.get_widget("loginDialog")
		self._parentWindow = widgetTree.get_widget("mainWindow")
		self._serviceCombo = widgetTree.get_widget("serviceCombo")
		self._usernameEntry = widgetTree.get_widget("usernameentry")
		self._passwordEntry = widgetTree.get_widget("passwordentry")

		self._serviceList = gtk.ListStore(gobject.TYPE_INT, gobject.TYPE_STRING)
		self._serviceCombo.set_model(self._serviceList)
		cell = gtk.CellRendererText()
		self._serviceCombo.pack_start(cell, True)
		self._serviceCombo.add_attribute(cell, 'text', 1)
		self._serviceCombo.set_active(0)

		callbackMapping = {
			"on_loginbutton_clicked": self._on_loginbutton_clicked,
			"on_loginclose_clicked": self._on_loginclose_clicked,
		}
		widgetTree.signal_autoconnect(callbackMapping)

	def request_credentials(self, parentWindow = None):
		"""
		@note UI Thread
		"""
		if parentWindow is None:
			parentWindow = self._parentWindow

		self._serviceCombo.hide()
		self._serviceList.clear()

		try:
			self._dialog.set_transient_for(parentWindow)
			self._dialog.set_default_response(gtk.RESPONSE_OK)
			response = self._dialog.run()
			if response != gtk.RESPONSE_OK:
				raise RuntimeError("Login Cancelled")

			username = self._usernameEntry.get_text()
			password = self._passwordEntry.get_text()
			self._passwordEntry.set_text("")
		finally:
			self._dialog.hide()

		return username, password

	def request_credentials_from(self, services, parentWindow = None):
		"""
		@note UI Thread
		"""
		if parentWindow is None:
			parentWindow = self._parentWindow

		self._serviceList.clear()
		for serviceIdserviceName in services.iteritems():
			self._serviceList.append(serviceIdserviceName)
		self._serviceCombo.set_active(0)
		self._serviceCombo.show()

		try:
			self._dialog.set_transient_for(parentWindow)
			self._dialog.set_default_response(gtk.RESPONSE_OK)
			response = self._dialog.run()
			if response != gtk.RESPONSE_OK:
				raise RuntimeError("Login Cancelled")

			username = self._usernameEntry.get_text()
			password = self._passwordEntry.get_text()
			self._passwordEntry.set_text("")
		finally:
			self._dialog.hide()

		itr = self._serviceCombo.get_active_iter()
		serviceId = int(self._serviceList.get_value(itr, 0))
		self._serviceList.clear()
		return serviceId, username, password

	def _on_loginbutton_clicked(self, *args):
		self._dialog.response(gtk.RESPONSE_OK)

	def _on_loginclose_clicked(self, *args):
		self._dialog.response(gtk.RESPONSE_CANCEL)


class ErrorDisplay(object):

	def __init__(self, widgetTree):
		super(ErrorDisplay, self).__init__()
		self.__errorBox = widgetTree.get_widget("errorEventBox")
		self.__errorDescription = widgetTree.get_widget("errorDescription")
		self.__errorClose = widgetTree.get_widget("errorClose")
		self.__parentBox = self.__errorBox.get_parent()

		self.__errorBox.connect("button_release_event", self._on_close)

		self.__messages = []
		self.__parentBox.remove(self.__errorBox)

	def push_message_with_lock(self, message):
		with gtk_lock():
			self.push_message(message)

	def push_message(self, message):
		if 0 < len(self.__messages):
			self.__messages.append(message)
		else:
			self.__show_message(message)

	def push_exception_with_lock(self, exception = None):
		with gtk_lock():
			self.push_exception(exception)

	def push_exception(self, exception = None):
		if exception is None:
			userMessage = str(sys.exc_value)
			warningMessage = str(traceback.format_exc())
		else:
			userMessage = str(exception)
			warningMessage = str(exception)
		self.push_message(userMessage)
		warnings.warn(warningMessage, stacklevel=3)

	def pop_message(self):
		if 0 < len(self.__messages):
			self.__show_message(self.__messages[0])
			del self.__messages[0]
		else:
			self.__hide_message()

	def _on_close(self, *args):
		self.pop_message()

	def __show_message(self, message):
		self.__errorDescription.set_text(message)
		self.__parentBox.pack_start(self.__errorBox, False, False)
		self.__parentBox.reorder_child(self.__errorBox, 1)

	def __hide_message(self):
		self.__errorDescription.set_text("")
		self.__parentBox.remove(self.__errorBox)


class DummyErrorDisplay(object):

	def __init__(self):
		super(DummyErrorDisplay, self).__init__()

		self.__messages = []

	def push_message_with_lock(self, message):
		self.push_message(message)

	def push_message(self, message):
		if 0 < len(self.__messages):
			self.__messages.append(message)
		else:
			self.__show_message(message)

	def push_exception(self, exception = None):
		if exception is None:
			warningMessage = traceback.format_exc()
		else:
			warningMessage = exception
		warnings.warn(warningMessage, stacklevel=3)

	def pop_message(self):
		if 0 < len(self.__messages):
			self.__show_message(self.__messages[0])
			del self.__messages[0]

	def __show_message(self, message):
		warnings.warn(message, stacklevel=2)


class MessageBox(gtk.MessageDialog):

	def __init__(self, message):
		parent = None
		gtk.MessageDialog.__init__(
			self,
			parent,
			gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
			gtk.MESSAGE_ERROR,
			gtk.BUTTONS_OK,
			message,
		)
		self.set_default_response(gtk.RESPONSE_OK)
		self.connect('response', self._handle_clicked)

	def _handle_clicked(self, *args):
		self.destroy()


class MessageBox2(gtk.MessageDialog):

	def __init__(self, message):
		parent = None
		gtk.MessageDialog.__init__(
			self,
			parent,
			gtk.DIALOG_DESTROY_WITH_PARENT,
			gtk.MESSAGE_ERROR,
			gtk.BUTTONS_OK,
			message,
		)
		self.set_default_response(gtk.RESPONSE_OK)
		self.connect('response', self._handle_clicked)

	def _handle_clicked(self, *args):
		self.destroy()


class PopupCalendar(object):

	def __init__(self, parent, displayDate, title = ""):
		self._displayDate = displayDate

		self._calendar = gtk.Calendar()
		self._calendar.select_month(self._displayDate.month, self._displayDate.year)
		self._calendar.select_day(self._displayDate.day)
		self._calendar.set_display_options(
			gtk.CALENDAR_SHOW_HEADING |
			gtk.CALENDAR_SHOW_DAY_NAMES |
			gtk.CALENDAR_NO_MONTH_CHANGE |
			0
		)
		self._calendar.connect("day-selected", self._on_day_selected)

		self._popupWindow = gtk.Window()
		self._popupWindow.set_title(title)
		self._popupWindow.add(self._calendar)
		self._popupWindow.set_transient_for(parent)
		self._popupWindow.set_modal(True)
		self._popupWindow.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
		self._popupWindow.set_skip_pager_hint(True)
		self._popupWindow.set_skip_taskbar_hint(True)

	def run(self):
		self._popupWindow.show_all()

	def _on_day_selected(self, *args):
		try:
			self._calendar.select_month(self._displayDate.month, self._displayDate.year)
			self._calendar.select_day(self._displayDate.day)
		except StandardError, e:
			warnings.warn(e.message)


class QuickAddView(object):

	def __init__(self, widgetTree, errorDisplay, signalSink, prefix):
		self._errorDisplay = errorDisplay
		self._manager = None
		self._signalSink = signalSink

		self._clipboard = gtk.clipboard_get()

		self._taskNameEntry = widgetTree.get_widget(prefix+"-nameEntry")
		self._addTaskButton = widgetTree.get_widget(prefix+"-addButton")
		self._pasteTaskNameButton = widgetTree.get_widget(prefix+"-pasteNameButton")
		self._clearTaskNameButton = widgetTree.get_widget(prefix+"-clearNameButton")
		self._onAddId = None
		self._onAddClickedId = None
		self._onAddReleasedId = None
		self._addToEditTimerId = None
		self._onClearId = None
		self._onPasteId = None

	def enable(self, manager):
		self._manager = manager

		self._onAddId = self._addTaskButton.connect("clicked", self._on_add)
		self._onAddClickedId = self._addTaskButton.connect("pressed", self._on_add_pressed)
		self._onAddReleasedId = self._addTaskButton.connect("released", self._on_add_released)
		self._onPasteId = self._pasteTaskNameButton.connect("clicked", self._on_paste)
		self._onClearId = self._clearTaskNameButton.connect("clicked", self._on_clear)

	def disable(self):
		self._manager = None

		self._addTaskButton.disconnect(self._onAddId)
		self._addTaskButton.disconnect(self._onAddClickedId)
		self._addTaskButton.disconnect(self._onAddReleasedId)
		self._pasteTaskNameButton.disconnect(self._onPasteId)
		self._clearTaskNameButton.disconnect(self._onClearId)

	def set_addability(self, addability):
		self._addTaskButton.set_sensitive(addability)

	def _on_add(self, *args):
		try:
			name = self._taskNameEntry.get_text()
			self._taskNameEntry.set_text("")

			self._signalSink.stage.send(("add", name))
		except StandardError, e:
			self._errorDisplay.push_exception()

	def _on_add_edit(self, *args):
		try:
			name = self._taskNameEntry.get_text()
			self._taskNameEntry.set_text("")

			self._signalSink.stage.send(("add-edit", name))
		except StandardError, e:
			self._errorDisplay.push_exception()

	def _on_add_pressed(self, widget):
		try:
			self._addToEditTimerId = gobject.timeout_add(1000, self._on_add_edit)
		except StandardError, e:
			self._errorDisplay.push_exception()

	def _on_add_released(self, widget):
		try:
			if self._addToEditTimerId is not None:
				gobject.source_remove(self._addToEditTimerId)
			self._addToEditTimerId = None
		except StandardError, e:
			self._errorDisplay.push_exception()

	def _on_paste(self, *args):
		try:
			entry = self._taskNameEntry.get_text()
			addedText = self._clipboard.wait_for_text()
			if addedText:
				entry += addedText
			self._taskNameEntry.set_text(entry)
		except StandardError, e:
			self._errorDisplay.push_exception()

	def _on_clear(self, *args):
		try:
			self._taskNameEntry.set_text("")
		except StandardError, e:
			self._errorDisplay.push_exception()


if __name__ == "__main__":
	if False:
		import datetime
		cal = PopupCalendar(None, datetime.datetime.now())
		cal._popupWindow.connect("destroy", lambda w: gtk.main_quit())
		cal.run()

	gtk.main()
