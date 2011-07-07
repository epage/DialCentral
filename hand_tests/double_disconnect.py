#!/usr/bin/env python

from __future__ import with_statement
from __future__ import division

import sys
import logging

PYSIDE = False
DISCONNECT_ON_DELETE = False

if PYSIDE:
	import PySide.QtCore as QtCore
	import PySide.QtGui as QtGui
else:
	import PyQt4.QtCore as QtCore
	import PyQt4.QtGui as QtGui


_moduleLogger = logging.getLogger(__name__)


class Signaller(QtCore.QObject):

	if PYSIDE:
		s1 = QtCore.Signal()
		s2 = QtCore.Signal()
	else:
		s1 = QtCore.pyqtSignal()
		s2 = QtCore.pyqtSignal()


class Window(object):

	def __init__(self, s):
		self._window = QtGui.QMainWindow()
		self._window.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
		self._window.setWindowTitle("Demo!")
		if DISCONNECT_ON_DELETE:
			self._window.destroyed.connect(self._on_destroyed)

		self._s = s
		self._s.s1.connect(self._on_signal)
		self._s.s2.connect(self._on_signal)

	def show(self):
		self._window.show()

	def _on_signal(self):
		print "Signal!"
		self._window.setWindowTitle("Signaled!")

	def _on_destroyed(self, obj = None):
		print "Main window destroyed"
		self._s.s1.disconnect(self._on_signal)
		self._s.s2.disconnect(self._on_signal)


if __name__ == "__main__":
	app = QtGui.QApplication([])

	s = Signaller()
	w = Window(s)
	w.show()

	val = app.exec_()
	del w

	print "s1"
	s.s1.emit()
	print "s2"
	s.s2.emit()

	print "Exiting"
	sys.exit(val)
