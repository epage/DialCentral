"""
@author:	  Laszlo Nagy
@copyright:   (c) 2005 by Szoftver Messias Bt.
@licence:	 BSD style

Objects of the MozillaEmulator class can emulate a browser that is capable of:

	- cookie management
	- configurable user agent string
	- GET and POST
	- multipart POST (send files)
	- receive content into file

I have seen many requests on the python mailing list about how to emulate a browser. I'm using this class for years now, without any problems. This is how you can use it:

	1. Use firefox
	2. Install and open the livehttpheaders plugin
	3. Use the website manually with firefox
	4. Check the GET and POST requests in the livehttpheaders capture window
	5. Create an instance of the above class and send the same GET and POST requests to the server.

Optional steps:

	- You can change user agent string in the build_opened method
	- The "encode_multipart_formdata" function can be used alone to create POST data from a list of field values and files
"""

import urllib2
import cookielib
import logging

import socket


_moduleLogger = logging.getLogger("browser_emu")
socket.setdefaulttimeout(20)


class MozillaEmulator(object):

	def __init__(self, trycount = 1):
		"""Create a new MozillaEmulator object.

		@param trycount: The download() method will retry the operation if it
		fails. You can specify -1 for infinite retrying.  A value of 0 means no
		retrying. A value of 1 means one retry. etc."""
		self.debug = False
		self.trycount = trycount
		self._cookies = cookielib.LWPCookieJar()
		self._loadedFromCookies = False

	def load_cookies(self, path):
		assert not self._loadedFromCookies, "Load cookies only once"
		if path is None:
			return

		self._cookies.filename = path
		try:
			self._cookies.load()
		except cookielib.LoadError:
			_moduleLogger.exception("Bad cookie file")
		except IOError:
			_moduleLogger.exception("No cookie file")
		except Exception, e:
			_moduleLogger.exception("Unknown error with cookies")
		else:
			self._loadedFromCookies = True

		return self._loadedFromCookies

	def save_cookies(self):
		if self._loadedFromCookies:
			self._cookies.save()

	def clear_cookies(self):
		if self._loadedFromCookies:
			self._cookies.clear()

	def download(self, url,
			postdata = None, extraheaders = None, forbidRedirect = False,
			trycount = None, only_head = False,
		):
		"""Download an URL with GET or POST methods.

		@param postdata: It can be a string that will be POST-ed to the URL.
			When None is given, the method will be GET instead.
		@param extraheaders: You can add/modify HTTP headers with a dict here.
		@param forbidRedirect: Set this flag if you do not want to handle
			HTTP 301 and 302 redirects.
		@param trycount: Specify the maximum number of retries here.
			0 means no retry on error. Using -1 means infinite retring.
			None means the default value (that is self.trycount).
		@param only_head: Create the openerdirector and return it. In other
			words, this will not retrieve any content except HTTP headers.

		@return: The raw HTML page data
		"""
		_moduleLogger.debug("Performing download of %s" % url)

		if extraheaders is None:
			extraheaders = {}
		if trycount is None:
			trycount = self.trycount
		cnt = 0

		while True:
			try:
				req, u = self._build_opener(url, postdata, extraheaders, forbidRedirect)
				openerdirector = u.open(req)
				if self.debug:
					_moduleLogger.info("%r - %r" % (req.get_method(), url))
					_moduleLogger.info("%r - %r" % (openerdirector.code, openerdirector.msg))
					_moduleLogger.info("%r" % (openerdirector.headers))
				self._cookies.extract_cookies(openerdirector, req)
				if only_head:
					return openerdirector

				return self._read(openerdirector, trycount)
			except urllib2.URLError, e:
				_moduleLogger.debug("%s: %s" % (e, url))
				cnt += 1
				if (-1 < trycount) and (trycount < cnt):
					raise

			# Retry :-)
			_moduleLogger.debug("MozillaEmulator: urllib2.URLError, retrying %d" % cnt)

	def _build_opener(self, url, postdata = None, extraheaders = None, forbidRedirect = False):
		if extraheaders is None:
			extraheaders = {}

		txheaders = {
			'Accept': 'text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png',
			'Accept-Language': 'en,en-us;q=0.5',
			'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
		}
		for key, value in extraheaders.iteritems():
			txheaders[key] = value
		req = urllib2.Request(url, postdata, txheaders)
		self._cookies.add_cookie_header(req)
		if forbidRedirect:
			redirector = HTTPNoRedirector()
			#_moduleLogger.info("Redirection disabled")
		else:
			redirector = urllib2.HTTPRedirectHandler()
			#_moduleLogger.info("Redirection enabled")

		http_handler = urllib2.HTTPHandler(debuglevel=self.debug)
		https_handler = urllib2.HTTPSHandler(debuglevel=self.debug)

		u = urllib2.build_opener(
			http_handler,
			https_handler,
			urllib2.HTTPCookieProcessor(self._cookies),
			redirector
		)
		u.addheaders = [(
			'User-Agent',
			'Mozilla/5.0 (Windows; U; Windows NT 5.1; de; rv:1.9.1.4) Gecko/20091016 Firefox/3.5.4 (.NET CLR 3.5.30729)'
		)]
		if not postdata is None:
			req.add_data(postdata)
		return (req, u)

	def _read(self, openerdirector, trycount):
		chunks = []

		chunk = openerdirector.read()
		chunks.append(chunk)
		#while chunk and cnt < trycount:
		#	time.sleep(1)
		#	cnt += 1
		#	chunk = openerdirector.read()
		#	chunks.append(chunk)

		data = "".join(chunks)

		if "Content-Length" in openerdirector.info():
			assert len(data) == int(openerdirector.info()["Content-Length"]), "The packet header promised %s of data but only was able to read %s of data" % (
				openerdirector.info()["Content-Length"],
				len(data),
			)

		return data


class HTTPNoRedirector(urllib2.HTTPRedirectHandler):
	"""This is a custom http redirect handler that FORBIDS redirection."""

	def http_error_302(self, req, fp, code, msg, headers):
		e = urllib2.HTTPError(req.get_full_url(), code, msg, headers, fp)
		if e.code in (301, 302):
			if 'location' in headers:
				newurl = headers.getheaders('location')[0]
			elif 'uri' in headers:
				newurl = headers.getheaders('uri')[0]
			e.newurl = newurl
		_moduleLogger.info("New url: %s" % e.newurl)
		raise e
