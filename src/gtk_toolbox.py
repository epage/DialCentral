#!/usr/bin/python


import gtk


class LoginWindow(object):

	def __init__(self, widgetTree):
		"""
		@note Thread agnostic
		"""
		self._dialog = widgetTree.get_widget("loginDialog")
		self._parentWindow = widgetTree.get_widget("mainWindow")
		self._usernameEntry = widgetTree.get_widget("usernameentry")
		self._passwordEntry = widgetTree.get_widget("passwordentry")

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

	def push_message(self, message):
		if 0 < len(self.__messages):
			self.__messages.append(message)
		else:
			self.__show_message(message)

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
