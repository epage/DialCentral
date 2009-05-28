import gobject
import gtk

class Program(object):

	def add_window(self, window):
		pass


class Window(gtk.Window, object):

	def set_menu(self, menu):
		self._hildonMenu = menu


gobject.type_register(Window)


def hildon_helper_set_thumb_scrollbar(widget, value):
	pass
