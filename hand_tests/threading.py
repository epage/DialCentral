#!/usr/bin/env python

from __future__ import with_statement
from __future__ import division

import time

import sys
sys.path.insert(0,"./src")
from util import qt_compat
QtCore = qt_compat.QtCore


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


class _WorkerThread(QtCore.QObject):

	_taskComplete  = qt_compat.Signal(object)

	def __init__(self, futureThread):
		QtCore.QObject.__init__(self)
		self._futureThread = futureThread
		self._futureThread._addTask.connect(self._on_task_added)
		self._taskComplete.connect(self._futureThread._on_task_complete)

	@qt_compat.Slot(object)
	def _on_task_added(self, task):
		if not self._futureThread._isRunning:
			print "Dropping task"

		func, args, kwds, on_success, on_error = task

		try:
			result = func(*args, **kwds)
			isError = False
		except Exception, e:
			print "Error, passing it back to the main thread"
			result = e
			isError = True

		taskResult = on_success, on_error, isError, result
		self._taskComplete.emit(taskResult)


class FutureThread(QtCore.QObject):

	_addTask = qt_compat.Signal(object)

	def __init__(self):
		QtCore.QObject.__init__(self)
		self._thread = QThread44()
		self._isRunning = False
		self._worker = _WorkerThread(self)
		self._worker.moveToThread(self._thread)

	def start(self):
		self._thread.start()
		self._isRunning = True

	def stop(self):
		self._isRunning = False
		self._thread.quit()

	def add_task(self, func, args, kwds, on_success, on_error):
		assert self._isRunning, "Task queue not started"
		task = func, args, kwds, on_success, on_error
		self._addTask.emit(task)

	@qt_compat.Slot(object)
	def _on_task_complete(self, taskResult):
		on_success, on_error, isError, result = taskResult
		if not self._isRunning:
			if isError:
				print "Masking: %s" % (result, )
			isError = True
			result = StopIteration("Cancelling all callbacks")
		callback = on_success if not isError else on_error
		try:
			callback(result)
		except Exception:
			print "Callback errored"


class Producer(QtCore.QObject):

	data = qt_compat.Signal(int)
	done = qt_compat.Signal()

	def __init__(self):
		QtCore.QObject.__init__(self)

	@qt_compat.Slot()
	def process(self):
		print "Starting producer"
		for i in xrange(10):
			self.data.emit(i)
			time.sleep(0.1)
		self.done.emit()


class Consumer(QtCore.QObject):

	def __init__(self):
		QtCore.QObject.__init__(self)

	@qt_compat.Slot()
	def process(self):
		print "Starting consumer"

	@qt_compat.Slot()
	def print_done(self):
		print "Done"

	@qt_compat.Slot(int)
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
	print "Status %s" % app.exec_()


def run_task():
	app = QtCore.QCoreApplication([])

	bright = FutureThread()
	def on_failure(*args):
		print "Failure", args

	def on_success(*args):
		print "Success", args

	def task(*args):
		print "Task", args

	timer = QtCore.QTimer()
	timeouts = [0]
	@qt_compat.Slot()
	def on_timeout():
		timeouts[0] += 1
		print timeouts[0]
		bright.add_task(task, (timeouts[0], ), {}, on_success, on_failure)
		if timeouts[0] == 5:
			timer.stop()
			bright.stop()
			app.exit(0)
	timer.timeout.connect(on_timeout)
	timer.start(10)
	bright.start()

	print "Status %s" % app.exec_()


if __name__ == "__main__":
	run_producer_consumer()
	#run_task()
