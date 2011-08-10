import logging

import gobject
import gst

import util.misc as misc_utils


_moduleLogger = logging.getLogger(__name__)


class Stream(gobject.GObject):

	# @bug Advertising state changes a bit early, should watch for GStreamer state change

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

	def __init__(self):
		gobject.GObject.__init__(self)
		#Fields
		self._uri = ""
		self._elapsed = 0
		self._duration = 0

		#Set up GStreamer
		self._player = gst.element_factory_make("playbin2", "player")
		bus = self._player.get_bus()
		bus.add_signal_watch()
		bus.connect("message", self._on_message)

		#Constants
		self._timeFormat = gst.Format(gst.FORMAT_TIME)
		self._seekFlag = gst.SEEK_FLAG_FLUSH

	@property
	def playing(self):
		return self.state == self.STATE_PLAY

	@property
	def has_file(self):
		return 0 < len(self._uri)

	@property
	def state(self):
		state = self._player.get_state()[1]
		return self._translate_state(state)

	def set_file(self, uri):
		if self._uri != uri:
			self._invalidate_cache()
		if self.state != self.STATE_STOP:
			self.stop()

		self._uri = uri
		self._player.set_property("uri", uri)

	def play(self):
		if self.state == self.STATE_PLAY:
			_moduleLogger.info("Already play")
			return
		_moduleLogger.info("Play")
		self._player.set_state(gst.STATE_PLAYING)
		self.emit("state-change", self.STATE_PLAY)

	def pause(self):
		if self.state == self.STATE_PAUSE:
			_moduleLogger.info("Already pause")
			return
		_moduleLogger.info("Pause")
		self._player.set_state(gst.STATE_PAUSED)
		self.emit("state-change", self.STATE_PAUSE)

	def stop(self):
		if self.state == self.STATE_STOP:
			_moduleLogger.info("Already stop")
			return
		self._player.set_state(gst.STATE_NULL)
		_moduleLogger.info("Stopped")
		self.emit("state-change", self.STATE_STOP)

	@property
	def elapsed(self):
		try:
			self._elapsed = self._player.query_position(self._timeFormat, None)[0]
		except:
			pass
		return self._elapsed

	@property
	def duration(self):
		try:
			self._duration = self._player.query_duration(self._timeFormat, None)[0]
		except:
			_moduleLogger.exception("Query failed")
		return self._duration

	def seek_time(self, ns):
		self._elapsed = ns
		self._player.seek_simple(self._timeFormat, self._seekFlag, ns)

	def _invalidate_cache(self):
		self._elapsed = 0
		self._duration = 0

	def _translate_state(self, gstState):
		return {
			gst.STATE_NULL: self.STATE_STOP,
			gst.STATE_PAUSED: self.STATE_PAUSE,
			gst.STATE_PLAYING: self.STATE_PLAY,
		}.get(gstState, self.STATE_STOP)

	@misc_utils.log_exception(_moduleLogger)
	def _on_message(self, bus, message):
		t = message.type
		if t == gst.MESSAGE_EOS:
			self._player.set_state(gst.STATE_NULL)
			self.emit("eof", self._uri)
		elif t == gst.MESSAGE_ERROR:
			self._player.set_state(gst.STATE_NULL)
			err, debug = message.parse_error()
			_moduleLogger.error("Error: %s, (%s)" % (err, debug))
			self.emit("error", err, debug)


gobject.type_register(Stream)
