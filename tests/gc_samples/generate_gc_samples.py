#!/usr/bin/env python

import sys
import urllib
import urllib2
import traceback
import warnings

import sys
sys.path.append("../../src")

import browser_emu
import gc_backend

	_forwardselectURL = "http://www.grandcentral.com/mobile/settings/forwarding_select"
	_loginURL = "https://www.grandcentral.com/mobile/account/login"
	_setforwardURL = "http://www.grandcentral.com/mobile/settings/set_forwarding?from=settings"
	_clicktocallURL = "http://www.grandcentral.com/mobile/calls/click_to_call?a_t=%s&destno=%s"
	_inboxallURL = "http://www.grandcentral.com/mobile/messages/inbox?types=all"
	_contactsURL = "http://www.grandcentral.com/mobile/contacts"
	_contactDetailURL = "http://www.grandcentral.com/mobile/contacts/detail"
webpages = [
	("forward", gc_backend.GCDialer._forwardselectURL),
	("login", gc_backend.GCDialer._loginURL),
	("setforward", gc_backend.GCDialer._setforwardURL),
	("clicktocall", gc_backend.GCDialer._clicktocallURL),
	("recent", gc_backend.GCDialer._inboxallURL),
	("contacts", gc_backend.GCDialer._contactsURL),
	("contactdetails", gc_backend.GCDialer._contactDetailURL),
]


browser = browser_emu.MozillaEmulator(1)
for name, url in webpages:
	try:
		page = browser.download(url)
	except StandardError, e:
		print e.message
		continue
	with open("not_loggedin_%s.txt" % name, "w") as f:
		f.write(page)

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
	loginSuccessOrFailurePage = browser.download(gc_backend.GCDialer._loginURL, loginPostData)
except urllib2.URLError, e:
	warnings.warn(traceback.format_exc())
	raise RuntimeError("%s is not accesible" % gc_backend.GCDialer._loginURL)

forwardPage = browser.download(gc_backend.GCDialer._forwardURL)

tokenGroup = gc_backend.GCDialer._tokenRe.search(forwardPage)
if tokenGroup is None:
	print forwardPage
	raise RuntimeError("Could not extract authentication token from GoogleVoice")
token = tokenGroup.group(1)

browser = browser_emu.MozillaEmulator(1)
for name, url in webpages:
	try:
		#data = urllib.urlencode({
		#	"_rnr_se": token,
		#})
		#page = browser.download(url, data)
		page = browser.download(url)
	except StandardError, e:
		warnings.warn(traceback.format_exc())
		continue
	print "Writing to file"
	with open("loggedin_%s.txt" % name, "w") as f:
		f.write(page)
