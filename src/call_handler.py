#!/usr/bin/env python

from __future__ import with_statement
from __future__ import division

import logging

from PyQt4 import QtCore
import dbus
try:
	import telepathy as _telepathy
	import util.tp_utils as telepathy_utils
	telepathy = _telepathy
except ImportError:
	telepathy = None

import util.misc as misc_utils


_moduleLogger = logging.getLogger(__name__)


class _FakeSignaller(object):

	def start(self):
		pass

	def stop(self):
		pass


class _MissedCallWatcher(QtCore.QObject):

	callMissed = QtCore.pyqtSignal()

	def __init__(self):
		QtCore.QObject.__init__(self)
		self._isStarted = False
		self._isSupported = True

		self._newChannelSignaller = telepathy_utils.NewChannelSignaller(self._on_new_channel)
		self._outstandingRequests = []

	@property
	def isSupported(self):
		return self._isSupported

	@property
	def isStarted(self):
		return self._isStarted

	def start(self):
		if self._isStarted:
			_moduleLogger.info("voicemail monitor already started")
			return
		try:
			self._newChannelSignaller.start()
		except RuntimeError:
			_moduleLogger.exception("Missed call detection not supported")
			self._newChannelSignaller = _FakeSignaller()
			self._isSupported = False
		self._isStarted = True

	def stop(self):
		if not self._isStarted:
			_moduleLogger.info("voicemail monitor stopped without starting")
			return
		_moduleLogger.info("Stopping voicemail refresh")
		self._newChannelSignaller.stop()

		# I don't want to trust whether the cancel happens within the current
		# callback or not which could be the deciding factor between invalid
		# iterators or infinite loops
		localRequests = [r for r in self._outstandingRequests]
		for request in localRequests:
			localRequests.cancel()

		self._isStarted = False

	@misc_utils.log_exception(_moduleLogger)
	def _on_new_channel(self, bus, serviceName, connObjectPath, channelObjectPath, channelType):
		if channelType != telepathy.interfaces.CHANNEL_TYPE_STREAMED_MEDIA:
			return

		conn = telepathy.client.Connection(serviceName, connObjectPath)
		try:
			chan = telepathy.client.Channel(serviceName, channelObjectPath)
		except dbus.exceptions.UnknownMethodException:
			_moduleLogger.exception("Client might not have implemented a deprecated method")
			return
		missDetection = telepathy_utils.WasMissedCall(
			bus, conn, chan, self._on_missed_call, self._on_error_for_missed
		)
		self._outstandingRequests.append(missDetection)

	@misc_utils.log_exception(_moduleLogger)
	def _on_missed_call(self, missDetection):
		_moduleLogger.info("Missed a call")
		self.callMissed.emit()
		self._outstandingRequests.remove(missDetection)

	@misc_utils.log_exception(_moduleLogger)
	def _on_error_for_missed(self, missDetection, reason):
		_moduleLogger.debug("Error: %r claims %r" % (missDetection, reason))
		self._outstandingRequests.remove(missDetection)


class _DummyMissedCallWatcher(QtCore.QObject):

	callMissed = QtCore.pyqtSignal()

	def __init__(self):
		QtCore.QObject.__init__(self)
		self._isStarted = False

	@property
	def isSupported(self):
		return False

	@property
	def isStarted(self):
		return self._isStarted

	def start(self):
		self._isStarted = True

	def stop(self):
		if not self._isStarted:
			_moduleLogger.info("voicemail monitor stopped without starting")
			return
		_moduleLogger.info("Stopping voicemail refresh")
		self._isStarted = False


if telepathy is not None:
	MissedCallWatcher = _MissedCallWatcher
else:
	MissedCallWatcher = _DummyMissedCallWatcher


if __name__ == "__main__":
	pass

