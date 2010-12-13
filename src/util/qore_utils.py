import logging

from PyQt4 import QtCore

import misc


_moduleLogger = logging.getLogger(__name__)


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


class _ParentThread(QtCore.QObject):

	def __init__(self, pool):
		QtCore.QObject.__init__(self)
		self._pool = pool

	@QtCore.pyqtSlot(object)
	@misc.log_exception(_moduleLogger)
	def _on_task_complete(self, taskResult):
		on_success, on_error, isError, result = taskResult
		if not self._pool._isRunning:
			if isError:
				_moduleLogger.error("Masking: %s" % (result, ))
			isError = True
			result = StopIteration("Cancelling all callbacks")
		callback = on_success if not isError else on_error
		try:
			callback(result)
		except Exception:
			_moduleLogger.exception("Callback errored")


class _WorkerThread(QtCore.QObject):

	taskComplete  = QtCore.pyqtSignal(object)

	def __init__(self, pool):
		QtCore.QObject.__init__(self)
		self._pool = pool

	@QtCore.pyqtSlot(object)
	@misc.log_exception(_moduleLogger)
	def _on_task_added(self, task):
		if not self._pool._isRunning:
			_moduleLogger.error("Dropping task")

		func, args, kwds, on_success, on_error = task

		try:
			result = func(*args, **kwds)
			isError = False
		except Exception, e:
			_moduleLogger.error("Error, passing it back to the main thread")
			result = e
			isError = True

		taskResult = on_success, on_error, isError, result
		self.taskComplete.emit(taskResult)

	@QtCore.pyqtSlot()
	@misc.log_exception(_moduleLogger)
	def _on_stop_requested(self):
		self._pool._thread.quit()


class AsyncPool(QtCore.QObject):

	_addTask = QtCore.pyqtSignal(object)
	_stopPool = QtCore.pyqtSignal()

	def __init__(self):
		QtCore.QObject.__init__(self)
		self._thread = QThread44()
		self._isRunning = True
		self._parent = _ParentThread(self)
		self._worker = _WorkerThread(self)
		self._worker.moveToThread(self._thread)

		self._addTask.connect(self._worker._on_task_added)
		self._worker.taskComplete.connect(self._parent._on_task_complete)
		self._stopPool.connect(self._worker._on_stop_requested)

	def start(self):
		self._thread.start()

	def stop(self):
		self._isRunning = False
		self._stopPool.emit()

	def add_task(self, func, args, kwds, on_success, on_error):
		assert self._isRunning, "Task queue not started"
		task = func, args, kwds, on_success, on_error
		self._addTask.emit(task)
