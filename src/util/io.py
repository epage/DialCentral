#!/usr/bin/env python


from __future__ import with_statement

import os
import pickle
import contextlib
import itertools
import functools


@contextlib.contextmanager
def change_directory(directory):
	previousDirectory = os.getcwd()
	os.chdir(directory)
	currentDirectory = os.getcwd()

	try:
		yield previousDirectory, currentDirectory
	finally:
		os.chdir(previousDirectory)


@contextlib.contextmanager
def pickled(filename):
	"""
	Here is an example usage:
	with pickled("foo.db") as p:
		p("users", list).append(["srid", "passwd", 23])
	"""

	if os.path.isfile(filename):
		data = pickle.load(open(filename))
	else:
		data = {}

	def getter(item, factory):
		if item in data:
			return data[item]
		else:
			data[item] = factory()
			return data[item]

	yield getter

	pickle.dump(data, open(filename, "w"))


@contextlib.contextmanager
def redirect(object_, attr, value):
	"""
	>>> import sys
	... with redirect(sys, 'stdout', open('stdout', 'w')):
	... 	print "hello"
	...
	>>> print "we're back"
	we're back
	"""
	orig = getattr(object_, attr)
	setattr(object_, attr, value)
	try:
		yield
	finally:
		setattr(object_, attr, orig)


def pathsplit(path):
	"""
	>>> pathsplit("/a/b/c")
	['', 'a', 'b', 'c']
	>>> pathsplit("./plugins/builtins.ini")
	['.', 'plugins', 'builtins.ini']
	"""
	pathParts = path.split(os.path.sep)
	return pathParts


def commonpath(l1, l2, common=None):
	"""
	>>> commonpath(pathsplit('/a/b/c/d'), pathsplit('/a/b/c1/d1'))
	(['', 'a', 'b'], ['c', 'd'], ['c1', 'd1'])
	>>> commonpath(pathsplit("./plugins/"), pathsplit("./plugins/builtins.ini"))
	(['.', 'plugins'], [''], ['builtins.ini'])
	>>> commonpath(pathsplit("./plugins/builtins"), pathsplit("./plugins"))
	(['.', 'plugins'], ['builtins'], [])
	"""
	if common is None:
		common = []

	if l1 == l2:
		return l1, [], []

	for i, (leftDir, rightDir) in enumerate(zip(l1, l2)):
		if leftDir != rightDir:
			return l1[0:i], l1[i:], l2[i:]
	else:
		if leftDir == rightDir:
			i += 1
		return l1[0:i], l1[i:], l2[i:]


def relpath(p1, p2):
	"""
	>>> relpath('/', '/')
	'./'
	>>> relpath('/a/b/c/d', '/')
	'../../../../'
	>>> relpath('/a/b/c/d', '/a/b/c1/d1')
	'../../c1/d1'
	>>> relpath('/a/b/c/d', '/a/b/c1/d1/')
	'../../c1/d1'
	>>> relpath("./plugins/builtins", "./plugins")
	'../'
	>>> relpath("./plugins/", "./plugins/builtins.ini")
	'builtins.ini'
	"""
	sourcePath = os.path.normpath(p1)
	destPath = os.path.normpath(p2)

	(common, sourceOnly, destOnly) = commonpath(pathsplit(sourcePath), pathsplit(destPath))
	if len(sourceOnly) or len(destOnly):
		relParts = itertools.chain(
			(('..' + os.sep) * len(sourceOnly), ),
			destOnly,
		)
		return os.path.join(*relParts)
	else:
		return "."+os.sep
