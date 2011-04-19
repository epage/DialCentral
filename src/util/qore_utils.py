import logging

import qt_compat
QtCore = qt_compat.QtCore

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


class _WorkerThread(QtCore.QObject):

	_taskComplete  = qt_compat.Signal(object)

	def __init__(self, futureThread):
		QtCore.QObject.__init__(self)
		self._futureThread = futureThread
		self._futureThread._addTask.connect(self._on_task_added)
		self._taskComplete.connect(self._futureThread._on_task_complete)

	@qt_compat.Slot(object)
	def _on_task_added(self, task):
		self.__on_task_added(task)

	@misc.log_exception(_moduleLogger)
	def __on_task_added(self, task):
		if not self._futureThread._isRunning:
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
		self.__on_task_complete(taskResult)

	@misc.log_exception(_moduleLogger)
	def __on_task_complete(self, taskResult):
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
