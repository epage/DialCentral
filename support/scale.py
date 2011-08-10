#!/usr/bin/env python

from __future__ import with_statement
from __future__ import division

import os
import logging

from PIL import Image


_moduleLogger = logging.getLogger(__name__)


def main(args):
	import optparse
	parser = optparse.OptionParser()
	parser.add_option(
		"--input", dest="input",
		help="Input image to scale", metavar="INPUT"
	)
	parser.add_option(
		"--output", dest="output",
		help="Scaled image", metavar="OUTPUT"
	)
	parser.add_option(
		"--size", dest="size",
		help="Icon size", metavar="SIZE"
	)
	options, positional  = parser.parse_args(args)
	if positional:
		parser.error("No positional arguments supported")
	if None in [options.input, options.output, options.size]:
		parser.error("Missing argument")
	if options.size == "guess":
		parts = reversed(os.path.split(options.output))
		for part in parts:
			try:
				options.size = int(part)
				_moduleLogger.info("Assuming image size of %r" % options.size)
				break
			except ValueError:
				pass

	icon = Image.open(options.input)
	icon.thumbnail((options.size, options.size), Image.ANTIALIAS)
	icon.save(options.output)


if __name__ == "__main__":
	import sys
	retcode = main(sys.argv[1:])
	sys.exit(retcode)
