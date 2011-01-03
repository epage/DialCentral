#!/usr/bin/env python

from __future__ import with_statement
from __future__ import division

import sys
import logging

from PyQt4 import QtCore
from PyQt4 import QtGui


_moduleLogger = logging.getLogger(__name__)


class QPieDisplay(QtGui.QWidget):

	def __init__(self, parent = None, flags = QtCore.Qt.Window):
		QtGui.QWidget.__init__(self, parent, flags)
		self._child = None
		self._size = QtCore.QSize(128, 128)
		self._canvas = QtGui.QPixmap(self._size)
		self._mask = QtGui.QBitmap(self._canvas.size())
		self._mask.fill(QtCore.Qt.color0)
		self._generate_mask(self._mask)
		self._canvas.setMask(self._mask)

	def sizeHint(self):
		return self._size

	def showEvent(self, showEvent):
		self.setMask(self._mask)

		QtGui.QWidget.showEvent(self, showEvent)

	def paintEvent(self, paintEvent):
		painter = QtGui.QPainter(self._canvas)
		painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
		adjustmentRect = self._canvas.rect().adjusted(0, 0, -1, -1)

		painter.setBrush(self.palette().window())
		painter.setPen(self.palette().mid().color())
		painter.drawRect(self._canvas.rect())

		background = self.palette().highlight().color()
		painter.setPen(QtCore.Qt.NoPen)
		painter.setBrush(background)
		painter.drawPie(adjustmentRect, 0, 360 * 16)

		dark = self.palette().mid().color()
		painter.setPen(QtGui.QPen(dark, 1))
		painter.setBrush(QtCore.Qt.NoBrush)
		painter.drawEllipse(adjustmentRect)

		screen = QtGui.QPainter(self)
		screen.drawPixmap(QtCore.QPoint(0, 0), self._canvas)
		QtGui.QWidget.paintEvent(self, paintEvent)

	def mousePressEvent(self, mouseEvent):
		pass

	def mouseReleaseEvent(self, mouseEvent):
		if self._child is None:
			lastMousePos = mouseEvent.pos()
			globalButtonPos = self.mapToGlobal(lastMousePos)
			self._child = QPieDisplay(None, QtCore.Qt.SplashScreen)
			self._child.move(globalButtonPos)
			self._child.show()
		else:
			self._child.hide()
			self._child = None

	def _generate_mask(self, mask):
		"""
		Specifies on the mask the shape of the pie menu
		"""
		painter = QtGui.QPainter(mask)
		painter.setPen(QtCore.Qt.color1)
		painter.setBrush(QtCore.Qt.color1)
		painter.drawRect(mask.rect())

class Grid(object):

	def __init__(self):
		layout = QtGui.QGridLayout()
		for i in xrange(3):
			for k in xrange(3):
				button = QtGui.QPushButton("%s,%s" % (i, k))
				button.setSizePolicy(QtGui.QSizePolicy(
					QtGui.QSizePolicy.MinimumExpanding,
					QtGui.QSizePolicy.MinimumExpanding,
					QtGui.QSizePolicy.PushButton,
				))
				self._create_callback(button)
				layout.addWidget(button, i, k)

		centralWidget = QtGui.QWidget()
		centralWidget.setLayout(layout)
		centralWidget.setContentsMargins(0, 0, 0, 0)

		self._window = QtGui.QMainWindow()
		self._window.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
		self._window.setWindowTitle("Buttons!")
		self._window.setCentralWidget(centralWidget)
		self._child = None

	def show(self):
		self._window.show()

	def _create_callback(self, button):
		button.clicked.connect(lambda: self._on_click(button))

	def _on_click(self, button):
		if self._child is None:
			buttonCorner = pos = QtCore.QPoint(0, 0)
			globalButtonPos = button.mapToGlobal(pos)
			self._child = QPieDisplay(None, QtCore.Qt.SplashScreen)
			self._child.move(globalButtonPos)
			self._child.show()
		else:
			self._child.hide()
			self._child = None


if __name__ == "__main__":
	app = QtGui.QApplication([])

	grid = Grid()
	grid.show()

	val = app.exec_()
	sys.exit(val)
