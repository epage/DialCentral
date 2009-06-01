#!/usr/bin/env python

import os
import urllib
import urllib2
import traceback
import warnings

import sys
sys.path.append("../../src")

import browser_emu
import gv_backend

# Create Browser
browser = browser_emu.MozillaEmulator(1)
cookieFile = os.path.join(".", ".gv_cookies.txt")
browser.cookies.filename = cookieFile

# Login
username = sys.argv[1]
password = sys.argv[2]

loginPostData = urllib.urlencode({
	'Email' : username,
	'Passwd' : password,
	'service': "grandcentral",
	"ltmpl": "mobile",
	"btmpl": "mobile",
	"PersistentCookie": "yes",
})

try:
	loginSuccessOrFailurePage = browser.download(gv_backend.GVDialer._loginURL, loginPostData)
except urllib2.URLError, e:
	warnings.warn(traceback.format_exc())
	raise RuntimeError("%s is not accesible" % gv_backend.GVDialer._loginURL)

forwardPage = browser.download(gv_backend.GVDialer._forwardURL)

tokenGroup = gv_backend.GVDialer._tokenRe.search(forwardPage)
if tokenGroup is None:
	print forwardPage
	raise RuntimeError("Could not extract authentication token from GoogleVoice")
token = tokenGroup.group(1)


with open("cookies.txt", "w") as f:
	f.writelines(
		"%s: %s\n" % (c.name, c.value)
		for c in browser.cookies
	)
