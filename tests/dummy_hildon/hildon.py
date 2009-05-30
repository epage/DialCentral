import gobject
import gtk

class FileChooserDialog(gtk.FileChooserDialog):
	"""
	@bug The buttons currently don't do anything
	"""

	def __init__(self, *args, **kwds):
		super(FileChooserDialog, self).__init__(*args, **kwds)
		self.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
		self.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)


class Program(object):

	def add_window(self, window):
		pass


class Window(gtk.Window, object):

	def __init__(self):
		super(Window, self).__init__(gtk.WINDOW_TOPLEVEL)
		self.set_default_size(700, 500)

	def set_menu(self, menu):
		self._hildonMenu = menu


gobject.type_register(Window)


def hildon_helper_set_thumb_scrollbar(widget, value):
	pass
