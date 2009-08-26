#!/usr/bin/env python


import gtk


class FakeHildonModule(object):
	pass


try:
	import hildon
except ImportError:
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
		renderer.set_property(scale=1.5)
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


class WidgetSwapper(object):

	def __init__(self, parentWidget, newWidget = None):
		self._parentWidget = parentWidget
		self._oldWidget = parentWidget.get_child()

		self._activeWidget = self._oldWidget
		self._widget = newWidget if newWidget is not None else self._oldWidget
		self._isEnabled = False

	def enable(self):
		assert not self._isEnabled, "Internal Error"
		self._parentWidget.remove(self._oldWidget)
		self._parentWidget.add(self._widget)
		self._activeWidget = self.widget

	def disable(self):
		assert self._isEnabled, "Internal Error"
		self._parentWidget.remove(self._widget)
		self._parentWidget.add(self._oldWidget)
		self._activeWidget = self._oldWidget

	@property
	def activeWidget(self):
		return self._activeWidget

	@property
	def widget(self):
		return self._widget


if IS_HILDON:
	def create_number_swapper(parentWidget):
		return WidgetSwapper(parentWidget, hildon.NumberEditor())
else:
	def create_number_swapper(parentWidget):
		return WidgetSwapper(parentWidget)
