#!/usr/bin/env python

from __future__ import with_statement
from __future__ import division

import time

import PyQt4.QtCore as QtCore


class QThread44(QtCore.QThread):
	"""
	This is to imitate QThread in Qt 4.4+ for when running on older version
	See http://labs.trolltech.com/blogs/2010/06/17/youre-doing-it-wrong
	(On Lucid I have Qt 4.7 and this is still an issue)
	"""

	def __init__(self, parent = None):
		QtCore.QThread.__init__(self, parent)

	def run(self):
		self.exec_()


class Producer(QtCore.QObject):

	data = QtCore.pyqtSignal(int)
	done = QtCore.pyqtSignal()

	def __init__(self):
		QtCore.QObject.__init__(self)

	@QtCore.pyqtSlot()
	def process(self):
		print "Starting producer"
		for i in xrange(10):
			self.data.emit(i)
			time.sleep(0.1)
		self.done.emit()


class Consumer(QtCore.QObject):

	def __init__(self):
		QtCore.QObject.__init__(self)

	@QtCore.pyqtSlot()
	def process(self):
		print "Starting consumer"

	@QtCore.pyqtSlot()
	def print_done(self):
		print "Done"

	@QtCore.pyqtSlot(int)
	def print_data(self, i):
		print i


if __name__ == "__main__":
	app = QtCore.QCoreApplication([])

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

	@QtCore.pyqtSlot()
	def producer_done():
		print "Shutting down"
		producerThread.quit()
		consumerThread.quit()
		print "Done"
	producer.done.connect(producer_done)

	count = [0]

	@QtCore.pyqtSlot()
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
