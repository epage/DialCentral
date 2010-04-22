#!/usr/bin/env python

from __future__ import with_statement
import itertools


verbose = False


def tag_parser(file, tag):
	"""
	>>> nothing = []
	>>> for todo in tag_parser(nothing, "@todo"):
	... 	print todo
	...
	>>> one = ["@todo Help!"]
	>>> for todo in tag_parser(one, "@todo"):
	... 	print todo
	...
	1: @todo Help!
	>>> mixed = ["one", "@todo two", "three"]
	>>> for todo in tag_parser(mixed, "@todo"):
	... 	print todo
	...
	2: @todo two
	>>> embedded = ["one @todo two", "three"]
	>>> for todo in tag_parser(embedded, "@todo"):
	... 	print todo
	...
	1: @todo two
	>>> continuation = ["one", "@todo two", " three"]
	>>> for todo in tag_parser(continuation, "@todo"):
	... 	print todo
	...
	2: @todo two three
	>>> series = ["one", "@todo two", "@todo three"]
	>>> for todo in tag_parser(series, "@todo"):
	... 	print todo
	...
	2: @todo two
	3: @todo three
	"""
	currentTodo = []
	prefix = None
	for lineNumber, line in enumerate(file):
		column = line.find(tag)
		if column != -1:
			if currentTodo:
				yield "\n".join (currentTodo)
			prefix = line[0:column]
			currentTodo = ["%d: %s" % (lineNumber+1, line[column:].strip())]
		elif prefix is not None and len(prefix)+1 < len(line) and line.startswith(prefix) and line[len(prefix)].isspace():
			currentTodo.append (line[len(prefix):].rstrip())
		elif currentTodo:
			yield "\n".join (currentTodo)
			currentTodo = []
			prefix = None
	if currentTodo:
		yield "\n".join (currentTodo)


def tag_finder(filename, tag):
	todoList = []

	with open(filename) as file:
		body = "\n".join (tag_parser(file, tag))
	passed = not body
	if passed:
		output = "No %s's for %s" % (tag, filename) if verbose else ""
	else:
		header = "%s's for %s:\n" % (tag, filename) if verbose else ""
		output = header + body
		output += "\n" if verbose else ""

	return (passed, output)


if __name__ == "__main__":
	import sys
	import os
	import optparse

	opar = optparse.OptionParser()
	opar.add_option("-v", "--verbose", dest="verbose", help="Toggle verbosity", action="store_true", default=False)
	options, args = opar.parse_args(sys.argv[1:])
	verbose = options.verbose

	bugsAsError = True
	todosAsError = False

	completeOutput = []
	allPassed = True
	for filename in args:
		bugPassed, bugOutput = tag_finder(filename, "@bug")
		todoPassed, todoOutput = tag_finder(filename, "@todo")
		output = "\n".join ([bugOutput, todoOutput])
		if (not bugPassed and bugsAsError) or (not todoPassed and todosAsError):
			allPassed = False
		output = output.strip()
		if output:
			completeOutput.append(filename+":\n"+output+"\n\n")
	print "\n".join(completeOutput)
	
	sys.exit(0 if allPassed else 1);
