#!/usr/bin/env python


import gtk


class FakeHildonModule(object):
	pass


try:
	import hildon
except (ImportError, OSError):
	hildon = FakeHildonModule


IS_HILDON = hildon is not FakeHildonModule


class FakeHildonProgram(object):

	pass


if IS_HILDON:
	def get_app_class():
		return hildon.Program
else:
	def get_app_class():
		return FakeHildonProgram


if IS_HILDON:
	def set_application_title(window, title):
		pass
else:
	def set_application_title(window, title):
		window.set_title(title)


if IS_HILDON:
	def hildonize_window(app, window):
		oldWindow = window
		newWindow = hildon.Window()
		oldWindow.get_child().reparent(newWindow)
		app.add_window(newWindow)
		return newWindow
else:
	def hildonize_window(app, window):
		return window


if IS_HILDON:
	def hildonize_menu(window, gtkMenu):
		hildonMenu = gtk.Menu()
		for child in gtkMenu.get_children():
			child.reparent(hildonMenu)
		window.set_menu(hildonMenu)
		gtkMenu.destroy()
		return hildonMenu
else:
	def hildonize_menu(window, gtkMenu):
		return gtkMenu


if IS_HILDON:
	def set_cell_thumb_selectable(renderer):
		renderer.set_property("scale", 1.5)
else:
	def set_cell_thumb_selectable(renderer):
		pass


if IS_HILDON:
	def hildonize_text_entry(textEntry):
		textEntry.set_property('hildon-input-mode', 7)
else:
	def hildonize_text_entry(textEntry):
		pass


if IS_HILDON:
	def hildonize_password_entry(textEntry):
		textEntry.set_property('hildon-input-mode', 7 | (1 << 29))
else:
	def hildonize_password_entry(textEntry):
		pass


if IS_HILDON:
	def hildonize_combo_entry(comboEntry):
		comboEntry.set_property('hildon-input-mode', 1 << 4)
else:
	def hildonize_combo_entry(textEntry):
		pass


if IS_HILDON:
	def set_thumb_scrollbar(scrolledWindow):
		hildon.hildon_helper_set_thumb_scrollbar(scrolledWindow, True)
else:
	def set_thumb_scrollbar(scrolledWindow):
		pass


if IS_HILDON:
	def request_number(parent, title, range, default):
		spinner = hildon.NumberEditor(*range)
		spinner.set_value(default)

		dialog = gtk.Dialog(
			title,
			parent,
			gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
			(gtk.STOCK_OK, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL),
		)
		dialog.set_default_response(gtk.RESPONSE_CANCEL)
		dialog.get_child().add(spinner)

		try:
			dialog.show_all()
			response = dialog.run()
		finally:
			dialog.hide()

		if response == gtk.RESPONSE_OK:
			return spinner.get_value()
		elif response == gtk.RESPONSE_CANCEL or response == gtk.RESPONSE_DELETE_EVENT:
			raise RuntimeError("User cancelled request")
		else:
			raise RuntimeError("Unrecognized response %r", response)
else:
	def request_number(parent, title, range, default):
		adjustment = gtk.Adjustment(default, range[0], range[1], 1, 5, 0)
		spinner = gtk.SpinButton(adjustment, 0, 0)
		spinner.set_wrap(False)

		dialog = gtk.Dialog(
			title,
			parent,
			gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
			(gtk.STOCK_OK, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL),
		)
		dialog.set_default_response(gtk.RESPONSE_CANCEL)
		dialog.get_child().add(spinner)

		try:
			dialog.show_all()
			response = dialog.run()
		finally:
			dialog.hide()

		if response == gtk.RESPONSE_OK:
			return spinner.get_value_as_int()
		elif response == gtk.RESPONSE_CANCEL or response == gtk.RESPONSE_DELETE_EVENT:
			raise RuntimeError("User cancelled request")
		else:
			raise RuntimeError("Unrecognized response %r", response)
