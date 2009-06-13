#!/usr/bin/env python

import os
import urllib
import urllib2
import traceback
import warnings

import sys
sys.path.append("../../src")

import browser_emu
import gc_backend

webpages = [
	("forward", gc_backend.GCDialer._forwardselectURL),
	("login", gc_backend.GCDialer._loginURL),
	("setforward", gc_backend.GCDialer._setforwardURL),
	("clicktocall", gc_backend.GCDialer._clicktocallURL),
	("recent", gc_backend.GCDialer._inboxallURL),
	("contacts", gc_backend.GCDialer._contactsURL),
]


# Create Browser
browser = browser_emu.MozillaEmulator(1)
cookieFile = os.path.join(".", ".gc_cookies.txt")
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
	'username' : username,
	'password' : password,
})

try:
	loginSuccessOrFailurePage = browser.download(gc_backend.GCDialer._loginURL, loginPostData)
except urllib2.URLError, e:
	warnings.warn(traceback.format_exc())
	raise RuntimeError("%s is not accesible" % gc_backend.GCDialer._loginURL)

forwardPage = browser.download(gc_backend.GCDialer._forwardselectURL)

tokenGroup = gc_backend.GCDialer._accessTokenRe.search(forwardPage)
if tokenGroup is None:
	print "="*60
	print forwardPage
	print "="*60
	raise RuntimeError("Could not extract authentication token from GrandCentral")
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
