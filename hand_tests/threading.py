#!/usr/bin/env python

from __future__ import with_statement
from __future__ import division

import time

import sys
sys.path.insert(0,"./src")
from util import qt_compat


class QThread44(qt_compat.QtCore.QThread):
	"""
	This is to imitate QThread in Qt 4.4+ for when running on older version
	See http://labs.trolltech.com/blogs/2010/06/17/youre-doing-it-wrong
	(On Lucid I have Qt 4.7 and this is still an issue)
	"""

	def __init__(self, parent = None):
		qt_compat.QtCore.QThread.__init__(self, parent)

	def run(self):
		self.exec_()


class Producer(qt_compat.QtCore.QObject):

	data = qt_compat.Signal(int)
	done = qt_compat.Signal()

	def __init__(self):
		qt_compat.QtCore.QObject.__init__(self)

	@qt_compat.Slot()
	def process(self):
		print "Starting producer"
		for i in xrange(10):
			self.data.emit(i)
			time.sleep(0.1)
		self.done.emit()


class Consumer(qt_compat.QtCore.QObject):

	def __init__(self):
		qt_compat.QtCore.QObject.__init__(self)

	@qt_compat.Slot()
	def process(self):
		print "Starting consumer"

	@qt_compat.Slot()
	def print_done(self):
		print "Done"

	@qt_compat.Slot(int)
	def print_data(self, i):
		print i


if __name__ == "__main__":
	app = qt_compat.QtCore.QCoreApplication([])

	producerThread = QThread44()
	producer = Producer()
	producer.moveToThread(producerThread)
	producerThread.started.connect(producer.process)

	consumerThread = QThread44()
	consumer = Consumer()
	consumer.moveToThread(consumerThread)
	consumerThread.started.connect(consumer.process)

	producer.data.connect(consumer.print_data)
	producer.done.connect(consumer.print_done)

	@qt_compat.Slot()
	def producer_done():
		print "Shutting down"
		producerThread.quit()
		consumerThread.quit()
		print "Done"
	producer.done.connect(producer_done)

	count = [0]

	@qt_compat.Slot()
	def thread_done():
		print "Thread done"
		count[0] += 1
		if count[0] == 2:
			print "Quitting"
			app.exit(0)
		print "Done"
	producerThread.finished.connect(thread_done)
	consumerThread.finished.connect(thread_done)

	producerThread.start()
	consumerThread.start()
	print "Status", app.exec_()
