#!/usr/bin/env python

from __future__ import with_statement
from __future__ import division

import functools
import time


FORCE_PYQT = False
DECORATE = True


try:
	if FORCE_PYQT:
		raise ImportError()
	import PySide.QtCore as _QtCore
	QtCore = _QtCore
	USES_PYSIDE = True
except ImportError:
	import sip
	sip.setapi('QString', 2)
	sip.setapi('QVariant', 2)
	import PyQt4.QtCore as _QtCore
	QtCore = _QtCore
	USES_PYSIDE = False


if USES_PYSIDE:
	Signal = QtCore.Signal
	Slot = QtCore.Slot
	Property = QtCore.Property
else:
	Signal = QtCore.pyqtSignal
	Slot = QtCore.pyqtSlot
	Property = QtCore.pyqtProperty


def log_exception():

	def log_exception_decorator(func):

		@functools.wraps(func)
		def wrapper(*args, **kwds):
			try:
				return func(*args, **kwds)
			except Exception:
				print "Exception", func.__name__
				raise

		if DECORATE:
			return wrapper
		else:
			return func

	return log_exception_decorator


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

	data = Signal(int)
	done = Signal()

	def __init__(self):
		QtCore.QObject.__init__(self)

	@Slot()
	@log_exception()
	def process(self):
		print "Starting producer"
		for i in xrange(10):
			self.data.emit(i)
			time.sleep(0.1)
		self.done.emit()


class Consumer(QtCore.QObject):

	def __init__(self):
		QtCore.QObject.__init__(self)

	@Slot()
	@log_exception()
	def process(self):
		print "Starting consumer"

	@Slot()
	@log_exception()
	def print_done(self):
		print "Done"

	@Slot(int)
	@log_exception()
	def print_data(self, i):
		print i


def run_producer_consumer():
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

	@Slot()
	@log_exception()
	def producer_done():
		print "Shutting down"
		producerThread.quit()
		consumerThread.quit()
		print "Done"
	producer.done.connect(producer_done)

	count = [0]

	@Slot()
	@log_exception()
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
	print "Status %s" % app.exec_()


if __name__ == "__main__":
	run_producer_consumer()
