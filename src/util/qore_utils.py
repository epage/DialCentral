import logging

from PyQt4 import QtCore

import misc


_moduleLogger = logging.getLogger(__name__)


class ParentThreadSignals(QtCore.QObject):

	taskComplete  = QtCore.pyqtSignal(object)


class WorkerThreadSignals(QtCore.QObject):

	addTask = QtCore.pyqtSignal(object)


class AsyncPool(QtCore.QObject):

	def __init__(self):
		_moduleLogger.info("main?")
		self._thread = QtCore.QThread()
		self._isRunning = True
		self._parent = ParentThreadSignals()
		self._parent.taskComplete.connect(self._on_task_complete)
		self._worker = WorkerThreadSignals()
		self._worker.moveToThread(self._thread)
		self._worker.addTask.connect(self._on_task_added)

	def start(self):
		_moduleLogger.info("main?")
		self._thread.exec_()

	def stop(self):
		_moduleLogger.info("main?")
		self._isRunning = False

	def add_task(self, func, args, kwds, on_success, on_error):
		_moduleLogger.info("main?")
		assert self._isRunning
		task = func, args, kwds, on_success, on_error
		self._worker.addTask.emit(task)

	@misc.log_exception(_moduleLogger)
	def _on_task_added(self, task):
		_moduleLogger.info("worker?")
		if not self._isRunning:
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
		self._parent.taskComplete.emit(taskResult)

	@misc.log_exception(_moduleLogger)
	def _on_task_complete(self, taskResult):
		_moduleLogger.info("main?")
		on_success, on_error, isError, result = taskResult
		if not self._isRunning:
			if isError:
				_moduleLogger.error("Masking: %s" % (result, ))
			isError = True
			result = StopIteration("Cancelling all callbacks")
		callback = on_success if not isError else on_error
		try:
			callback(result)
		except Exception:
			_moduleLogger.exception("Callback errored")
		return False
