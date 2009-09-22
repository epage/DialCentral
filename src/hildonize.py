#!/usr/bin/env python


import gobject
import gtk
import dbus


class _NullHildonModule(object):
	pass


try:
	import hildon as _hildon
	hildon  = _hildon # Dumb but gets around pyflakiness
except (ImportError, OSError):
	hildon = _NullHildonModule


IS_HILDON_SUPPORTED = hildon is not _NullHildonModule


class _NullHildonProgram(object):

	def add_window(self, window):
		pass


def _hildon_get_app_class():
	return hildon.Program


def _null_get_app_class():
	return _NullHildonProgram


if IS_HILDON_SUPPORTED:
	get_app_class = _hildon_get_app_class
else:
	get_app_class = _null_get_app_class


def _hildon_set_application_title(window, title):
	pass


def _null_set_application_title(window, title):
	window.set_title(title)


if IS_HILDON_SUPPORTED:
	set_application_title = _hildon_set_application_title
else:
	set_application_title = _null_set_application_title


def _fremantle_hildonize_window(app, window):
	oldWindow = window
	newWindow = hildon.StackableWindow()
	oldWindow.get_child().reparent(newWindow)
	app.add_window(newWindow)
	return newWindow


def _hildon_hildonize_window(app, window):
	oldWindow = window
	newWindow = hildon.Window()
	oldWindow.get_child().reparent(newWindow)
	app.add_window(newWindow)
	return newWindow


def _null_hildonize_window(app, window):
	return window


try:
	hildon.StackableWindow
	hildonize_window = _fremantle_hildonize_window
except AttributeError:
	try:
		hildon.Window
		hildonize_window = _hildon_hildonize_window
	except AttributeError:
		hildonize_window = _null_hildonize_window


def _fremantle_hildonize_menu(window, gtkMenu, buttons):
	appMenu = hildon.AppMenu()
	for button in buttons:
		appMenu.append(button)
	window.set_app_menu(appMenu)
	gtkMenu.get_parent().remove(gtkMenu)
	return appMenu


def _hildon_hildonize_menu(window, gtkMenu, ignoredButtons):
	hildonMenu = gtk.Menu()
	for child in gtkMenu.get_children():
		child.reparent(hildonMenu)
	window.set_menu(hildonMenu)
	gtkMenu.destroy()
	return hildonMenu


def _null_hildonize_menu(window, gtkMenu, ignoredButtons):
	return gtkMenu


try:
	hildon.AppMenu
	GTK_MENU_USED = False
	hildonize_menu = _fremantle_hildonize_menu
except AttributeError:
	GTK_MENU_USED = True
	if IS_HILDON_SUPPORTED:
		hildonize_menu = _hildon_hildonize_menu
	else:
		hildonize_menu = _null_hildonize_menu


def _hildon_set_cell_thumb_selectable(renderer):
	renderer.set_property("scale", 1.5)


def _null_set_cell_thumb_selectable(renderer):
	pass


if IS_HILDON_SUPPORTED:
	set_cell_thumb_selectable = _hildon_set_cell_thumb_selectable
else:
	set_cell_thumb_selectable = _null_set_cell_thumb_selectable


def _hildon_hildonize_text_entry(textEntry):
	textEntry.set_property('hildon-input-mode', 7)


def _null_hildonize_text_entry(textEntry):
	pass


if IS_HILDON_SUPPORTED:
	hildonize_text_entry = _hildon_hildonize_text_entry
else:
	hildonize_text_entry = _null_hildonize_text_entry


def _hildon_mark_window_rotatable(window):
	# gtk documentation is unclear whether this does a "=" or a "|="
	window.set_flags(hildon.HILDON_PORTRAIT_MODE_SUPPORT)


def _null_mark_window_rotatable(window):
	pass


try:
	hildon.HILDON_PORTRAIT_MODE_SUPPORT
	mark_window_rotatable = _hildon_mark_window_rotatable
except AttributeError:
	mark_window_rotatable = _null_mark_window_rotatable


def _hildon_window_to_portrait(window):
	# gtk documentation is unclear whether this does a "=" or a "|="
	window.set_flags(hildon.HILDON_PORTRAIT_MODE_SUPPORT)


def _hildon_window_to_landscape(window):
	# gtk documentation is unclear whether this does a "=" or a "&= ~"
	window.unset_flags(hildon.HILDON_PORTRAIT_MODE_REQUEST)


def _null_window_to_portrait(window):
	pass


def _null_window_to_landscape(window):
	pass


try:
	hildon.HILDON_PORTRAIT_MODE_SUPPORT
	hildon.HILDON_PORTRAIT_MODE_REQUEST

	window_to_portrait = _hildon_window_to_portrait
	window_to_landscape = _hildon_window_to_landscape
except AttributeError:
	window_to_portrait = _null_window_to_portrait
	window_to_landscape = _null_window_to_landscape


def get_device_orientation():
	bus = dbus.SystemBus()
	try:
		rawMceRequest = bus.get_object("com.nokia.mce", "/com/nokia/mce/request")
		mceRequest = dbus.Interface(rawMceRequest, dbus_interface="com.nokia.mce.request")
		orientation, standState, faceState, xAxis, yAxis, zAxis = mceRequest.get_device_orientation()
	except dbus.exception.DBusException:
		# catching for documentation purposes that when a system doesn't
		# support this, this is what to expect
		raise

	if orientation == "":
		return gtk.ORIENTATION_HORIZONTAL
	elif orientation == "":
		return gtk.ORIENTATION_VERTICAL
	else:
		raise RuntimeError("Unknown orientation: %s" % orientation)


def _hildon_hildonize_password_entry(textEntry):
	textEntry.set_property('hildon-input-mode', 7 | (1 << 29))


def _null_hildonize_password_entry(textEntry):
	pass


if IS_HILDON_SUPPORTED:
	hildonize_password_entry = _hildon_hildonize_password_entry
else:
	hildonize_password_entry = _null_hildonize_password_entry


def _hildon_hildonize_combo_entry(comboEntry):
	comboEntry.set_property('hildon-input-mode', 1 << 4)


def _null_hildonize_combo_entry(textEntry):
	pass


if IS_HILDON_SUPPORTED:
	hildonize_combo_entry = _hildon_hildonize_combo_entry
else:
	hildonize_combo_entry = _null_hildonize_combo_entry


def _fremantle_hildonize_scrollwindow(scrolledWindow):
	pannableWindow = hildon.PannableArea()

	child = scrolledWindow.get_child()
	scrolledWindow.remove(child)
	pannableWindow.add(child)

	parent = scrolledWindow.get_parent()
	parent.remove(scrolledWindow)
	parent.add(pannableWindow)

	return pannableWindow


def _hildon_hildonize_scrollwindow(scrolledWindow):
	hildon.hildon_helper_set_thumb_scrollbar(scrolledWindow, True)
	return scrolledWindow


def _null_hildonize_scrollwindow(scrolledWindow):
	return scrolledWindow


try:
	hildon.PannableArea
	hildonize_scrollwindow = _fremantle_hildonize_scrollwindow
	hildonize_scrollwindow_with_viewport = _hildon_hildonize_scrollwindow
except AttributeError:
	try:
		hildon.hildon_helper_hildonize_scrollwindow
		hildonize_scrollwindow = _hildon_hildonize_scrollwindow
		hildonize_scrollwindow_with_viewport = _hildon_hildonize_scrollwindow
	except AttributeError:
		hildonize_scrollwindow = _null_hildonize_scrollwindow
		hildonize_scrollwindow_with_viewport = _null_hildonize_scrollwindow


def _hildon_request_number(parent, title, range, default):
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


def _null_request_number(parent, title, range, default):
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


try:
	hildon.NumberEditor # TODO deprecated in fremantle
	request_number = _hildon_request_number
except AttributeError:
	request_number = _null_request_number


def _hildon_touch_selector(parent, title, items, defaultIndex):
	model = gtk.ListStore(gobject.TYPE_STRING)
	for item in items:
		model.append((item, ))

	selector = hildon.TouchSelector()
	selector.append_text_column(model, True)
	selector.set_column_selection_mode(hildon.TOUCH_SELECTOR_SELECTION_MODE_SINGLE)
	selector.set_active(0, defaultIndex)

	dialog = hildon.PickerDialog(parent)
	dialog.set_selector(selector)

	try:
		dialog.show_all()
		response = dialog.run()
	finally:
		dialog.hide()

	if response == gtk.RESPONSE_OK:
		return selector.get_active(0)
	elif response == gtk.RESPONSE_CANCEL or response == gtk.RESPONSE_DELETE_EVENT:
		raise RuntimeError("User cancelled request")
	else:
		raise RuntimeError("Unrecognized response %r", response)


def _null_touch_selector(parent, title, items, defaultIndex = -1):
	model = gtk.ListStore(gobject.TYPE_STRING)
	for item in items:
		model.append((item, ))

	cell = gtk.CellRendererText()

	combo = gtk.ComboBox()
	combo.set_model(model)
	combo.pack_start(cell, True)
	combo.add_attribute(cell, 'text', 0)
	combo.set_active(defaultIndex)

	dialog = gtk.Dialog(
		title,
		parent,
		gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
		(gtk.STOCK_OK, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL),
	)
	dialog.set_default_response(gtk.RESPONSE_CANCEL)
	dialog.get_child().add(combo)

	try:
		dialog.show_all()
		response = dialog.run()
	finally:
		dialog.hide()

	if response == gtk.RESPONSE_OK:
		return combo.get_active()
	elif response == gtk.RESPONSE_CANCEL or response == gtk.RESPONSE_DELETE_EVENT:
		raise RuntimeError("User cancelled request")
	else:
		raise RuntimeError("Unrecognized response %r", response)


try:
	hildon.PickerDialog
	hildon.TouchSelector
	touch_selector = _hildon_touch_selector
except AttributeError:
	touch_selector = _null_touch_selector


if __name__ == "__main__":
	pass
