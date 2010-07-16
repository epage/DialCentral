#!/usr/bin/env python

from __future__ import with_statement

import os
import errno
import time
import functools
import contextlib


def synchronized(lock):
	"""
	Synchronization decorator.

	>>> import misc
	>>> misc.validate_decorator(synchronized(object()))
	"""

	def wrap(f):

		@functools.wraps(f)
		def newFunction(*args, **kw):
			lock.acquire()
			try:
				return f(*args, **kw)
			finally:
				lock.release()
		return newFunction
	return wrap


@contextlib.contextmanager
def qlock(queue, gblock = True, gtimeout = None, pblock = True, ptimeout = None):
	"""
	Locking with a queue, good for when you want to lock an item passed around

	>>> import Queue
	>>> item = 5
	>>> lock = Queue.Queue()
	>>> lock.put(item)
	>>> with qlock(lock) as i:
	... 	print i
	5
	"""
	item = queue.get(gblock, gtimeout)
	try:
		yield item
	finally:
		queue.put(item, pblock, ptimeout)


@contextlib.contextmanager
def flock(path, timeout=-1):
	WAIT_FOREVER = -1
	DELAY = 0.1
	timeSpent = 0

	acquired = False

	while timeSpent <= timeout or timeout == WAIT_FOREVER:
		try:
			fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
			acquired = True
			break
		except OSError, e:
			if e.errno != errno.EEXIST:
				raise
		time.sleep(DELAY)
		timeSpent += DELAY

	assert acquired, "Failed to grab file-lock %s within timeout %d" % (path, timeout)

	try:
		yield fd
	finally:
		os.unlink(path)
