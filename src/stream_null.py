#!/usr/bin/env python

from __future__ import with_statement
from __future__ import division

import logging


_moduleLogger = logging.getLogger(__name__)


class Stream(object):

	STATE_PLAY = "play"
	STATE_PAUSE = "pause"
	STATE_STOP = "stop"

	def __init__(self):
		pass

	def connect(self, signalName, slot):
		pass

	@property
	def playing(self):
		return False

	@property
	def has_file(self):
		return False

	@property
	def state(self):
		return self.STATE_STOP

	def set_file(self, uri):
		pass

	def play(self):
		pass

	def pause(self):
		pass

	def stop(self):
		pass

	@property
	def elapsed(self):
		return 0

	@property
	def duration(self):
		return 0

	def seek_time(self, ns):
		pass


if __name__ == "__main__":
	pass

