import logging

import gobject
import dbus

import util.misc as misc_utils


_moduleLogger = logging.getLogger(__name__)


class Stream(gobject.GObject):

	STATE_PLAY = "play"
	STATE_PAUSE = "pause"
	STATE_STOP = "stop"

	__gsignals__ = {
		'state-change' : (
			gobject.SIGNAL_RUN_LAST,
			gobject.TYPE_NONE,
			(gobject.TYPE_STRING, ),
		),
		'eof' : (
			gobject.SIGNAL_RUN_LAST,
			gobject.TYPE_NONE,
			(gobject.TYPE_STRING, ),
		),
		'error' : (
			gobject.SIGNAL_RUN_LAST,
			gobject.TYPE_NONE,
			(gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT),
		),
	}

	_SERVICE_NAME = "com.nokia.osso_media_server"
	_OBJECT_PATH = "/com/nokia/osso_media_server"
	_AUDIO_INTERFACE_NAME = "com.nokia.osso_media_server.music"

	def __init__(self):
		gobject.GObject.__init__(self)
		#Fields
		self._state = self.STATE_STOP
		self._nextState = self.STATE_STOP
		self._uri = ""
		self._elapsed = 0
		self._duration = 0

		session_bus = dbus.SessionBus()

		# Get the osso-media-player proxy object
		oms_object = session_bus.get_object(
			self._SERVICE_NAME,
			self._OBJECT_PATH,
			introspect=False,
			follow_name_owner_changes=True,
		)
		# Use the audio interface
		oms_audio_interface = dbus.Interface(
			oms_object,
			self._AUDIO_INTERFACE_NAME,
		)
		self._audioProxy = oms_audio_interface

		self._audioProxy.connect_to_signal("state_changed", self._on_state_changed)
		self._audioProxy.connect_to_signal("end_of_stream", self._on_end_of_stream)

		error_signals = [
			"no_media_selected",
			"file_not_found",
			"type_not_found",
			"unsupported_type",
			"gstreamer",
			"dsp",
			"device_unavailable",
			"corrupted_file",
			"out_of_memory",
			"audio_codec_not_supported",
		]
		for error in error_signals:
			self._audioProxy.connect_to_signal(error, self._on_error)

	@property
	def playing(self):
		return self.state == self.STATE_PLAY

	@property
	def has_file(self):
		return 0 < len(self._uri)

	@property
	def state(self):
		return self._state

	def set_file(self, uri):
		if self._uri != uri:
			self._invalidate_cache()
		if self.state != self.STATE_STOP:
			self.stop()

		self._uri = uri
		self._audioProxy.set_media_location(self._uri)

	def play(self):
		if self._nextState == self.STATE_PLAY:
			_moduleLogger.info("Already play")
			return
		_moduleLogger.info("Play")
		self._audioProxy.play()
		self._nextState = self.STATE_PLAY
		#self.emit("state-change", self.STATE_PLAY)

	def pause(self):
		if self._nextState == self.STATE_PAUSE:
			_moduleLogger.info("Already pause")
			return
		_moduleLogger.info("Pause")
		self._audioProxy.pause()
		self._nextState = self.STATE_PAUSE
		#self.emit("state-change", self.STATE_PLAY)

	def stop(self):
		if self._nextState == self.STATE_STOP:
			_moduleLogger.info("Already stop")
			return
		self._audioProxy.stop()
		_moduleLogger.info("Stopped")
		self._nextState = self.STATE_STOP
		#self.emit("state-change", self.STATE_STOP)

	@property
	def elapsed(self):
		pos_info = self._audioProxy.get_position()
		if isinstance(pos_info, tuple):
			self._elapsed, self._duration = pos_info
		return self._elapsed

	@property
	def duration(self):
		pos_info = self._audioProxy.get_position()
		if isinstance(pos_info, tuple):
			self._elapsed, self._duration = pos_info
		return self._duration

	def seek_time(self, ns):
		_moduleLogger.debug("Seeking to: %s", ns)
		self._audioProxy.seek( dbus.Int32(1), dbus.Int32(ns) )

	def _invalidate_cache(self):
		self._elapsed = 0
		self._duration = 0

	@misc_utils.log_exception(_moduleLogger)
	def _on_error(self, *args):
		err, debug = "", repr(args)
		_moduleLogger.error("Error: %s, (%s)" % (err, debug))
		self.emit("error", err, debug)

	@misc_utils.log_exception(_moduleLogger)
	def _on_end_of_stream(self, *args):
		self._state = self.STATE_STOP
		self._nextState = self.STATE_STOP
		self.emit("eof", self._uri)

	@misc_utils.log_exception(_moduleLogger)
	def _on_state_changed(self, state):
		_moduleLogger.info("State: %s", state)
		state = {
			"playing": self.STATE_PLAY,
			"paused": self.STATE_PAUSE,
			"stopped": self.STATE_STOP,
		}[state]
		if self._state == self.STATE_STOP and self._nextState == self.STATE_PLAY and state == self.STATE_STOP:
			# They seem to want to advertise stop right as the stream is starting, breaking the owner of this
			return
		self._state = state
		self._nextState = state
		self.emit("state-change", state)


gobject.type_register(Stream)
