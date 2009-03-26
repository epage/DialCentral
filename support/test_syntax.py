#!/usr/bin/env python

import commands


verbose = False


def syntax_test(file):
	commandTemplate = """
	python -t -t -W all -c "import py_compile; py_compile.compile ('%(filename)s', doraise=False)" """
	compileCommand = commandTemplate % {"filename": file}
	(status, text) = commands.getstatusoutput (compileCommand)
	text = text.rstrip()
	passed = len(text) == 0

	if passed:
		output = ("Syntax is correct for "+file) if verbose else ""
	else:
		output = ("Syntax is invalid for %s\n" % file) if verbose else ""
		output += text
	return (passed, output)


if __name__ == "__main__":
	import sys
	import os
	import optparse

	opar = optparse.OptionParser()
	opar.add_option("-v", "--verbose", dest="verbose", help="Toggle verbosity", action="store_true", default=False)
	options, args = opar.parse_args(sys.argv[1:])
	verbose = options.verbose

	completeOutput = []
	allPassed = True
	for filename in args:
		passed, output = syntax_test(filename)
		if not passed:
			allPassed = False
		if output.strip():
			completeOutput.append(output)
	print "\n".join(completeOutput)

	sys.exit(0 if allPassed else 1);
