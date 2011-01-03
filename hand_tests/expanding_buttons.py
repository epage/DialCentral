#!/usr/bin/env python

from __future__ import with_statement
from __future__ import division

import sys
import logging

from PyQt4 import QtCore
from PyQt4 import QtGui


_moduleLogger = logging.getLogger(__name__)


if __name__ == "__main__":
	app = QtGui.QApplication([])

	layout = QtGui.QGridLayout()
	for i in xrange(3):
		for k in xrange(3):
			button = QtGui.QPushButton("%s,%s" % (i, k))
			button.setSizePolicy(QtGui.QSizePolicy(
				QtGui.QSizePolicy.MinimumExpanding,
				QtGui.QSizePolicy.MinimumExpanding,
				QtGui.QSizePolicy.PushButton,
			))
			layout.addWidget(button, i, k)

	centralWidget = QtGui.QWidget()
	centralWidget.setLayout(layout)
	centralWidget.setContentsMargins(0, 0, 0, 0)

	window = QtGui.QMainWindow()
	window.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
	window.setWindowTitle("Buttons!")
	window.setCentralWidget(centralWidget)
	window.show()

	val = app.exec_()
	sys.exit(val)
