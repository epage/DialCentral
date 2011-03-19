#!/usr/bin/env python

from __future__ import with_statement
from __future__ import division

import logging

import util.qt_compat as qt_compat
QtCore = qt_compat.QtCore

import util.misc as misc_utils
try:
	import stream_gst
	stream = stream_gst
except ImportError:
	try:
		import stream_osso
		stream = stream_osso
	except ImportError:
		import stream_null
		stream = stream_null


_moduleLogger = logging.getLogger(__name__)


class StreamToken(QtCore.QObject):

	stateChange = qt_compat.Signal(str)
	invalidated = qt_compat.Signal()
	error = qt_compat.Signal(str)

	STATE_PLAY = stream.Stream.STATE_PLAY
	STATE_PAUSE = stream.Stream.STATE_PAUSE
	STATE_STOP = stream.Stream.STATE_STOP

	def __init__(self, stream):
		QtCore.QObject.__init__(self)
		self._stream = stream
		self._stream.connect("state-change", self._on_stream_state)
		self._stream.connect("eof", self._on_stream_eof)
		self._stream.connect("error", self._on_stream_error)

	@property
	def state(self):
		if self.isValid:
			return self._stream.state
		else:
			return self.STATE_STOP

	@property
	def isValid(self):
		return self._stream is not None

	def play(self):
		self._stream.play()

	def pause(self):
		self._stream.pause()

	def stop(self):
		self._stream.stop()

	def invalidate(self):
		if self._stream is None:
			return
		_moduleLogger.info("Playback token invalidated")
		self._stream = None

	@misc_utils.log_exception(_moduleLogger)
	def _on_stream_state(self, s, state):
		if not self.isValid:
			return
		if state == self.STATE_STOP:
			self.invalidate()
		self.stateChange.emit(state)

	@misc_utils.log_exception(_moduleLogger)
	def _on_stream_eof(self, s, uri):
		if not self.isValid:
			return
		self.invalidate()
		self.stateChange.emit(self.STATE_STOP)

	@misc_utils.log_exception(_moduleLogger)
	def _on_stream_error(self, s, error, debug):
		if not self.isValid:
			return
		_moduleLogger.info("Error %s %s" % (error, debug))
		self.error.emit(str(error))


class StreamHandler(QtCore.QObject):

	def __init__(self):
		QtCore.QObject.__init__(self)
		self._stream = stream.Stream()
		self._token = StreamToken(self._stream)

	def set_file(self, path):
		self._token.invalidate()
		self._token = StreamToken(self._stream)
		self._stream.set_file(path)
		return self._token

	@misc_utils.log_exception(_moduleLogger)
	def _on_stream_state(self, s, state):
		_moduleLogger.info("State change %r" % state)


if __name__ == "__main__":
	pass

