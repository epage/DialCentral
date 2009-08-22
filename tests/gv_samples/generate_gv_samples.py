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

webpages = [
	("login", gv_backend.GVDialer._loginURL),
	("contacts", gv_backend.GVDialer._contactsURL),
	("voicemail", gv_backend.GVDialer._voicemailURL),
	("sms", gv_backend.GVDialer._smsURL),
	("forward", gv_backend.GVDialer._forwardURL),
	("recent", gv_backend.GVDialer._recentCallsURL),
	("placed", gv_backend.GVDialer._placedCallsURL),
	("recieved", gv_backend.GVDialer._receivedCallsURL),
	("missed", gv_backend.GVDialer._missedCallsURL),
]


# Create Browser
browser = browser_emu.MozillaEmulator(1)
cookieFile = os.path.join(".", ".gv_cookies.txt")
browser.cookies.filename = cookieFile

# Get Pages
for name, url in webpages:
	try:
		page = browser.download(url)
	except StandardError, e:
		print e.message
		continue
	with open("not_loggedin_%s.txt" % name, "w") as f:
		f.write(page)

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
with open("loggingin.txt", "w") as f:
	f.write(page)

forwardPage = browser.download(gv_backend.GVDialer._forwardURL)

tokenGroup = gv_backend.GVDialer._tokenRe.search(forwardPage)
if tokenGroup is None:
	print forwardPage
	raise RuntimeError("Could not extract authentication token from GoogleVoice")
token = tokenGroup.group(1)

# Get Pages
for name, url in webpages:
	try:
		page = browser.download(url)
	except StandardError, e:
		warnings.warn(traceback.format_exc())
		continue
	print "Writing to file"
	with open("loggedin_%s.txt" % name, "w") as f:
		f.write(page)
