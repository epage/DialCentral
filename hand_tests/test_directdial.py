#!/usr/bin/env python

import sys
import logging


_moduleLogger = logging.getLogger(__name__)
sys.path.insert(0,"../src")

import backends.gvoice
import backends.browser_emu


def main(username, password, number):
	backends.browser_emu.USER_AGENT = "Mozilla/5.0 (iPhone; U; CPU iPhone OS 3_0 like Mac OS X; en-us) AppleWebKit/528.18 (KHTML, like Gecko) Version/4.0 Mobile/7A341 Safari/528.16"
	gvoice = backends.gvoice.GVoiceBackend()
	gvoice.login(username, password)
	for cookie in gvoice._browser._cookies:
		print "\t", cookie

	if False:
		page = gvoice._get_page_with_token(
			"https://www.google.com/voice/m/x",
			{
				"m": "call",
				"n": "18004664411",
				"f": "",
				"v": "6",
			},
		)
	elif True:
		page = gvoice._get_page_with_token(
			"https://www.google.com/voice/m/x?m=call&n=%s&f=&v=6" % "18004664411",
			{
			},
		)
	elif False:
		page = gvoice._get_page("http://www.useragentstring.com/")
	print page


if __name__ == "__main__":
	logging.basicConfig(level=logging.DEBUG)
	args = sys.argv[1:]
	main(args[0], args[1], "")
