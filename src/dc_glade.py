#!/usr/bin/python2.5

"""
DialCentral - Front end for Google's Grand Central service.
Copyright (C) 2008  Mark Bergman bergman AT merctech DOT com

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

@bug Crashes when switching contact lists, see http://talk.maemo.org/showpost.php?p=312920&postcount=176
@bug Refeshing SMS a lot, then go to contacts and send a message, see http://talk.maemo.org/showpost.php?p=312920&postcount=176
@bug Can't send sms from dialpad, see http://talk.maemo.org/showpost.php?p=312922&postcount=177
@bug Sending an sms from contacts gave an error
@bug Getting into a bad state on connection loss, see http://talk.maemo.org/showpost.php?p=312912&postcount=175

@todo Figure out how to integrate with the Maemo contacts app
@bug Session timeouts are bad, possible solutions:
	@li For every X minutes, if logged in, attempt login
	@li Restructure so code handling login/dial/sms is beneath everything else and login attempts are made if those fail
@todo Add logging support to make debugging issues for people a lot easier
"""


from __future__ import with_statement

import sys
import gc
import os
import threading
import base64
import ConfigParser
import itertools
import warnings

import gtk
import gtk.glade

try:
	import hildon
except ImportError:
	hildon = None

import constants
import gtk_toolbox


def getmtime_nothrow(path):
	try:
		return os.path.getmtime(path)
	except StandardError:
		return 0


def display_error_message(msg):
	error_dialog = gtk.MessageDialog(None, 0, gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE, msg)

	def close(dialog, response):
		dialog.destroy()
	error_dialog.connect("response", close)
	error_dialog.run()


class Dialcentral(object):

	_glade_files = [
		os.path.join(os.path.dirname(__file__), "dialcentral.glade"),
		os.path.join(os.path.dirname(__file__), "../lib/dialcentral.glade"),
		'/usr/lib/dialcentral/dialcentral.glade',
	]

	KEYPAD_TAB = 0
	RECENT_TAB = 1
	MESSAGES_TAB = 2
	CONTACTS_TAB = 3
	ACCOUNT_TAB = 4

	NULL_BACKEND = 0
	GC_BACKEND = 1
	GV_BACKEND = 2
	BACKENDS = (NULL_BACKEND, GC_BACKEND, GV_BACKEND)

	def __init__(self):
		self._initDone = False
		self._connection = None
		self._osso = None
		self._clipboard = gtk.clipboard_get()

		self._credentials = ("", "")
		self._selectedBackendId = self.NULL_BACKEND
		self._defaultBackendId = self.GC_BACKEND
		self._phoneBackends = None
		self._dialpads = None
		self._accountViews = None
		self._messagesViews = None
		self._recentViews = None
		self._contactsViews = None
		self._alarmHandler = None
		self._ledHandler = None
		self._originalCurrentLabels = []

		for path in self._glade_files:
			if os.path.isfile(path):
				self._widgetTree = gtk.glade.XML(path)
				break
		else:
			display_error_message("Cannot find dialcentral.glade")
			gtk.main_quit()
			return

		self._window = self._widgetTree.get_widget("mainWindow")
		self._notebook = self._widgetTree.get_widget("notebook")
		self._errorDisplay = gtk_toolbox.ErrorDisplay(self._widgetTree)
		self._credentialsDialog = gtk_toolbox.LoginWindow(self._widgetTree)

		self._app = None
		self._isFullScreen = False
		if hildon is not None:
			self._app = hildon.Program()
			oldWindow = self._window
			self._window = hildon.Window()
			oldWindow.get_child().reparent(self._window)
			self._app.add_window(self._window)

			try:
				self._widgetTree.get_widget("usernameentry").set_property('hildon-input-mode', 7)
				self._widgetTree.get_widget("passwordentry").set_property('hildon-input-mode', 7|(1 << 29))
				self._widgetTree.get_widget("callbackcombo").get_child().set_property('hildon-input-mode', (1 << 4))
			except TypeError, e:
				warnings.warn(e.message)
			hildon.hildon_helper_set_thumb_scrollbar(self._widgetTree.get_widget('recent_scrolledwindow'), True)
			hildon.hildon_helper_set_thumb_scrollbar(self._widgetTree.get_widget('message_scrolledwindow'), True)
			hildon.hildon_helper_set_thumb_scrollbar(self._widgetTree.get_widget('contacts_scrolledwindow'), True)

			gtkMenu = self._widgetTree.get_widget("dialpad_menubar")
			menu = gtk.Menu()
			for child in gtkMenu.get_children():
				child.reparent(menu)
			self._window.set_menu(menu)
			gtkMenu.destroy()

			self._window.connect("key-press-event", self._on_key_press)
			self._window.connect("window-state-event", self._on_window_state_change)
		else:
			pass # warnings.warn("No Hildon", UserWarning, 2)

		# If under hildon, rely on the application name being shown
		if hildon is None:
			self._window.set_title("%s" % constants.__pretty_app_name__)

		callbackMapping = {
			"on_dialpad_quit": self._on_close,
		}
		self._widgetTree.signal_autoconnect(callbackMapping)

		self._window.connect("destroy", self._on_close)
		self._window.set_default_size(800, 300)
		self._window.show_all()

		self._loginSink = gtk_toolbox.threaded_stage(
			gtk_toolbox.comap(
				self.attempt_login,
				gtk_toolbox.null_sink(),
			)
		)

		backgroundSetup = threading.Thread(target=self._idle_setup)
		backgroundSetup.setDaemon(True)
		backgroundSetup.start()

	def _idle_setup(self):
		"""
		If something can be done after the UI loads, push it here so it's not blocking the UI
		"""
		try:
			# Barebones UI handlers
			import null_backend
			import null_views

			self._phoneBackends = {self.NULL_BACKEND: null_backend.NullDialer()}
			with gtk_toolbox.gtk_lock():
				self._dialpads = {self.NULL_BACKEND: null_views.Dialpad(self._widgetTree)}
				self._accountViews = {self.NULL_BACKEND: null_views.AccountInfo(self._widgetTree)}
				self._recentViews = {self.NULL_BACKEND: null_views.RecentCallsView(self._widgetTree)}
				self._messagesViews = {self.NULL_BACKEND: null_views.MessagesView(self._widgetTree)}
				self._contactsViews = {self.NULL_BACKEND: null_views.ContactsView(self._widgetTree)}

				self._dialpads[self._selectedBackendId].enable()
				self._accountViews[self._selectedBackendId].enable()
				self._recentViews[self._selectedBackendId].enable()
				self._messagesViews[self._selectedBackendId].enable()
				self._contactsViews[self._selectedBackendId].enable()

			# Setup maemo specifics
			try:
				import osso
			except ImportError:
				osso = None
			self._osso = None
			if osso is not None:
				self._osso = osso.Context(constants.__app_name__, constants.__version__, False)
				device = osso.DeviceState(self._osso)
				device.set_device_state_callback(self._on_device_state_change, 0)
			else:
				pass # warnings.warn("No OSSO", UserWarning, 2)

			try:
				import alarm_handler
				self._alarmHandler = alarm_handler.AlarmHandler()
			except ImportError:
				alarm_handler = None
			except Exception:
				with gtk_toolbox.gtk_lock():
					self._errorDisplay.push_exception()
				alarm_handler = None
			if hildon is not None:
				import led_handler
				self._ledHandler = led_handler.LedHandler()

			# Setup maemo specifics
			try:
				import conic
			except ImportError:
				conic = None
			self._connection = None
			if conic is not None:
				self._connection = conic.Connection()
				self._connection.connect("connection-event", self._on_connection_change, constants.__app_magic__)
				self._connection.request_connection(conic.CONNECT_FLAG_NONE)
			else:
				pass # warnings.warn("No Internet Connectivity API ", UserWarning)

			# Setup costly backends
			import gv_backend
			import gc_backend
			import file_backend
			import gc_views

			try:
				os.makedirs(constants._data_path_)
			except OSError, e:
				if e.errno != 17:
					raise
			gcCookiePath = os.path.join(constants._data_path_, "gc_cookies.txt")
			gvCookiePath = os.path.join(constants._data_path_, "gv_cookies.txt")
			self._defaultBackendId = self._guess_preferred_backend((
				(self.GC_BACKEND, gcCookiePath),
				(self.GV_BACKEND, gvCookiePath),
			))

			self._phoneBackends.update({
				self.GC_BACKEND: gc_backend.GCDialer(gcCookiePath),
				self.GV_BACKEND: gv_backend.GVDialer(gvCookiePath),
			})
			with gtk_toolbox.gtk_lock():
				unifiedDialpad = gc_views.Dialpad(self._widgetTree, self._errorDisplay)
				unifiedDialpad.set_number("")
				self._dialpads.update({
					self.GC_BACKEND: unifiedDialpad,
					self.GV_BACKEND: unifiedDialpad,
				})
				self._accountViews.update({
					self.GC_BACKEND: gc_views.AccountInfo(
						self._widgetTree, self._phoneBackends[self.GC_BACKEND], None, self._errorDisplay
					),
					self.GV_BACKEND: gc_views.AccountInfo(
						self._widgetTree, self._phoneBackends[self.GV_BACKEND], self._alarmHandler, self._errorDisplay
					),
				})
				self._accountViews[self.GC_BACKEND].save_everything = lambda *args: None
				self._accountViews[self.GV_BACKEND].save_everything = self._save_settings
				self._recentViews.update({
					self.GC_BACKEND: gc_views.RecentCallsView(
						self._widgetTree, self._phoneBackends[self.GC_BACKEND], self._errorDisplay
					),
					self.GV_BACKEND: gc_views.RecentCallsView(
						self._widgetTree, self._phoneBackends[self.GV_BACKEND], self._errorDisplay
					),
				})
				self._messagesViews.update({
					self.GC_BACKEND: null_views.MessagesView(self._widgetTree),
					self.GV_BACKEND: gc_views.MessagesView(
						self._widgetTree, self._phoneBackends[self.GV_BACKEND], self._errorDisplay
					),
				})
				self._contactsViews.update({
					self.GC_BACKEND: gc_views.ContactsView(
						self._widgetTree, self._phoneBackends[self.GC_BACKEND], self._errorDisplay
					),
					self.GV_BACKEND: gc_views.ContactsView(
						self._widgetTree, self._phoneBackends[self.GV_BACKEND], self._errorDisplay
					),
				})

			fsContactsPath = os.path.join(constants._data_path_, "contacts")
			fileBackend = file_backend.FilesystemAddressBookFactory(fsContactsPath)
			for backendId in (self.GV_BACKEND, self.GC_BACKEND):
				self._dialpads[backendId].number_selected = self._select_action
				self._recentViews[backendId].number_selected = self._select_action
				self._messagesViews[backendId].number_selected = self._select_action
				self._contactsViews[backendId].number_selected = self._select_action

				addressBooks = [
					self._phoneBackends[backendId],
					fileBackend,
				]
				mergedBook = gc_views.MergedAddressBook(addressBooks, gc_views.MergedAddressBook.advanced_lastname_sorter)
				self._contactsViews[backendId].append(mergedBook)
				self._contactsViews[backendId].extend(addressBooks)
				self._contactsViews[backendId].open_addressbook(*self._contactsViews[backendId].get_addressbooks().next()[0][0:2])

			callbackMapping = {
				"on_paste": self._on_paste,
				"on_refresh": self._on_menu_refresh,
				"on_clearcookies_clicked": self._on_clearcookies_clicked,
				"on_notebook_switch_page": self._on_notebook_switch_page,
				"on_about_activate": self._on_about_activate,
			}
			self._widgetTree.signal_autoconnect(callbackMapping)

			with gtk_toolbox.gtk_lock():
				self._originalCurrentLabels = [
					self._notebook.get_tab_label(self._notebook.get_nth_page(pageIndex)).get_text()
					for pageIndex in xrange(self._notebook.get_n_pages())
				]
				self._notebookTapHandler = gtk_toolbox.TapOrHold(self._notebook)
				self._notebookTapHandler.enable()
			self._notebookTapHandler.on_tap = self._reset_tab_refresh
			self._notebookTapHandler.on_hold = self._on_tab_refresh
			self._notebookTapHandler.on_holding = self._set_tab_refresh
			self._notebookTapHandler.on_cancel = self._reset_tab_refresh

			self._initDone = True

			config = ConfigParser.SafeConfigParser()
			config.read(constants._user_settings_)
			with gtk_toolbox.gtk_lock():
				self.load_settings(config)

			self._spawn_attempt_login(2)
		except Exception, e:
			with gtk_toolbox.gtk_lock():
				self._errorDisplay.push_exception()

	def attempt_login(self, numOfAttempts = 10, force = False):
		"""
		@todo Handle user notification better like attempting to login and failed login

		@note This must be run outside of the UI lock
		"""
		try:
			assert 0 <= numOfAttempts, "That was pointless having 0 or less login attempts"
			assert self._initDone, "Attempting login before app is fully loaded"

			serviceId = self.NULL_BACKEND
			loggedIn = False
			if not force:
				try:
					self.refresh_session()
					serviceId = self._defaultBackendId
					loggedIn = True
				except StandardError, e:
					warnings.warn('Session refresh failed with the following message "%s"' % e.message, UserWarning, 2)

			if not loggedIn:
				loggedIn, serviceId = self._login_by_user(numOfAttempts)

			with gtk_toolbox.gtk_lock():
				self._change_loggedin_status(serviceId)
		except StandardError, e:
			with gtk_toolbox.gtk_lock():
				self._errorDisplay.push_exception()

	def _spawn_attempt_login(self, *args):
		self._loginSink.send(args)

	def refresh_session(self):
		"""
		@note Thread agnostic
		"""
		assert self._initDone, "Attempting login before app is fully loaded"

		loggedIn = False
		if not loggedIn:
			loggedIn = self._login_by_cookie()
		if not loggedIn:
			loggedIn = self._login_by_settings()

		if not loggedIn:
			raise RuntimeError("Login Failed")

	def _login_by_cookie(self):
		"""
		@note Thread agnostic
		"""
		loggedIn = self._phoneBackends[self._defaultBackendId].is_authed()
		if loggedIn:
			warnings.warn(
				"Logged into %r through cookies" % self._phoneBackends[self._defaultBackendId],
				UserWarning, 2
			)
		return loggedIn

	def _login_by_settings(self):
		"""
		@note Thread agnostic
		"""
		username, password = self._credentials
		loggedIn = self._phoneBackends[self._defaultBackendId].login(username, password)
		if loggedIn:
			self._credentials = username, password
			warnings.warn(
				"Logged into %r through settings" % self._phoneBackends[self._defaultBackendId],
				UserWarning, 2
			)
		return loggedIn

	def _login_by_user(self, numOfAttempts):
		"""
		@note This must be run outside of the UI lock
		"""
		loggedIn, (username, password) = False, self._credentials
		tmpServiceId = self.NULL_BACKEND
		for attemptCount in xrange(numOfAttempts):
			if loggedIn:
				break
			availableServices = (
				(self.GV_BACKEND, "Google Voice"),
				(self.GC_BACKEND, "Grand Central"),
			)
			with gtk_toolbox.gtk_lock():
				credentials = self._credentialsDialog.request_credentials_from(
					availableServices, defaultCredentials = self._credentials
				)
			tmpServiceId, username, password = credentials
			loggedIn = self._phoneBackends[tmpServiceId].login(username, password)

		if loggedIn:
			serviceId = tmpServiceId
			self._credentials = username, password
			warnings.warn(
				"Logged into %r through user request" % self._phoneBackends[serviceId],
				UserWarning, 2
			)
		else:
			serviceId = self.NULL_BACKEND

		return loggedIn, serviceId

	def _select_action(self, action, number, message):
		self.refresh_session()
		if action == "select":
			self._dialpads[self._selectedBackendId].set_number(number)
			self._notebook.set_current_page(self.KEYPAD_TAB)
		elif action == "dial":
			self._on_dial_clicked(number)
		elif action == "sms":
			self._on_sms_clicked(number, message)
		else:
			assert False, "Unknown action: %s" % action

	def _change_loggedin_status(self, newStatus):
		oldStatus = self._selectedBackendId
		if oldStatus == newStatus:
			return

		self._dialpads[oldStatus].disable()
		self._accountViews[oldStatus].disable()
		self._recentViews[oldStatus].disable()
		self._messagesViews[oldStatus].disable()
		self._contactsViews[oldStatus].disable()

		self._dialpads[newStatus].enable()
		self._accountViews[newStatus].enable()
		self._recentViews[newStatus].enable()
		self._messagesViews[newStatus].enable()
		self._contactsViews[newStatus].enable()

		if self._phoneBackends[self._selectedBackendId].get_callback_number() is None:
			self._phoneBackends[self._selectedBackendId].set_sane_callback()
		self._accountViews[self._selectedBackendId].update()

		self._selectedBackendId = newStatus

	def load_settings(self, config):
		"""
		@note UI Thread
		"""
		try:
			self._defaultBackendId = int(config.get(constants.__pretty_app_name__, "active"))
			blobs = (
				config.get(constants.__pretty_app_name__, "bin_blob_%i" % i)
				for i in xrange(len(self._credentials))
			)
			creds = (
				base64.b64decode(blob)
				for blob in blobs
			)
			self._credentials = tuple(creds)

			if self._alarmHandler is not None:
				self._alarmHandler.load_settings(config, "alarm")
		except ConfigParser.NoOptionError, e:
			warnings.warn(
				"Settings file %s is missing section %s" % (
					constants._user_settings_,
					e.section,
				),
				stacklevel=2
			)
		except ConfigParser.NoSectionError, e:
			warnings.warn(
				"Settings file %s is missing section %s" % (
					constants._user_settings_,
					e.section,
				),
				stacklevel=2
			)

		for backendId, view in itertools.chain(
			self._dialpads.iteritems(),
			self._accountViews.iteritems(),
			self._messagesViews.iteritems(),
			self._recentViews.iteritems(),
			self._contactsViews.iteritems(),
		):
			sectionName = "%s - %s" % (backendId, view.name())
			try:
				view.load_settings(config, sectionName)
			except ConfigParser.NoOptionError, e:
				warnings.warn(
					"Settings file %s is missing section %s" % (
						constants._user_settings_,
						e.section,
					),
					stacklevel=2
				)
			except ConfigParser.NoSectionError, e:
				warnings.warn(
					"Settings file %s is missing section %s" % (
						constants._user_settings_,
						e.section,
					),
					stacklevel=2
				)

	def save_settings(self, config):
		"""
		@note Thread Agnostic
		"""
		config.add_section(constants.__pretty_app_name__)
		config.set(constants.__pretty_app_name__, "active", str(self._selectedBackendId))
		for i, value in enumerate(self._credentials):
			blob = base64.b64encode(value)
			config.set(constants.__pretty_app_name__, "bin_blob_%i" % i, blob)
		config.add_section("alarm")
		if self._alarmHandler is not None:
			self._alarmHandler.save_settings(config, "alarm")

		for backendId, view in itertools.chain(
			self._dialpads.iteritems(),
			self._accountViews.iteritems(),
			self._messagesViews.iteritems(),
			self._recentViews.iteritems(),
			self._contactsViews.iteritems(),
		):
			sectionName = "%s - %s" % (backendId, view.name())
			config.add_section(sectionName)
			view.save_settings(config, sectionName)

	def _guess_preferred_backend(self, backendAndCookiePaths):
		modTimeAndPath = [
			(getmtime_nothrow(path), backendId, path)
			for backendId, path in backendAndCookiePaths
		]
		modTimeAndPath.sort()
		return modTimeAndPath[-1][1]

	def _save_settings(self):
		"""
		@note Thread Agnostic
		"""
		config = ConfigParser.SafeConfigParser()
		self.save_settings(config)
		with open(constants._user_settings_, "wb") as configFile:
			config.write(configFile)

	def _refresh_active_tab(self):
		pageIndex = self._notebook.get_current_page()
		if pageIndex == self.CONTACTS_TAB:
			self._contactsViews[self._selectedBackendId].update(force=True)
		elif pageIndex == self.RECENT_TAB:
			self._recentViews[self._selectedBackendId].update(force=True)
		elif pageIndex == self.MESSAGES_TAB:
			self._messagesViews[self._selectedBackendId].update(force=True)

		if pageIndex in (self.RECENT_TAB, self.MESSAGES_TAB):
			if self._ledHandler is not None:
				self._ledHandler.off()

	def _on_close(self, *args, **kwds):
		try:
			if self._osso is not None:
				self._osso.close()

			if self._initDone:
				self._save_settings()
		finally:
			gtk.main_quit()

	def _on_device_state_change(self, shutdown, save_unsaved_data, memory_low, system_inactivity, message, userData):
		"""
		For shutdown or save_unsaved_data, our only state is cookies and I think the cookie manager handles that for us.
		For system_inactivity, we have no background tasks to pause

		@note Hildon specific
		"""
		if memory_low:
			for backendId in self.BACKENDS:
				self._phoneBackends[backendId].clear_caches()
			self._contactsViews[self._selectedBackendId].clear_caches()
			gc.collect()

		if save_unsaved_data or shutdown:
			self._save_settings()

	def _on_connection_change(self, connection, event, magicIdentifier):
		"""
		@note Hildon specific
		"""
		import conic

		status = event.get_status()
		error = event.get_error()
		iap_id = event.get_iap_id()
		bearer = event.get_bearer_type()

		if status == conic.STATUS_CONNECTED:
			if self._initDone:
				self._spawn_attempt_login(2)
		elif status == conic.STATUS_DISCONNECTED:
			if self._initDone:
				self._defaultBackendId = self._selectedBackendId
				self._change_loggedin_status(self.NULL_BACKEND)

	def _on_window_state_change(self, widget, event, *args):
		"""
		@note Hildon specific
		"""
		if event.new_window_state & gtk.gdk.WINDOW_STATE_FULLSCREEN:
			self._isFullScreen = True
		else:
			self._isFullScreen = False

	def _on_key_press(self, widget, event, *args):
		"""
		@note Hildon specific
		"""
		if event.keyval == gtk.keysyms.F6:
			if self._isFullScreen:
				self._window.unfullscreen()
			else:
				self._window.fullscreen()

	def _on_clearcookies_clicked(self, *args):
		self._phoneBackends[self._selectedBackendId].logout()
		self._accountViews[self._selectedBackendId].clear()
		self._recentViews[self._selectedBackendId].clear()
		self._messagesViews[self._selectedBackendId].clear()
		self._contactsViews[self._selectedBackendId].clear()
		self._change_loggedin_status(self.NULL_BACKEND)

		self._spawn_attempt_login(2, True)

	def _on_notebook_switch_page(self, notebook, page, pageIndex):
		self._reset_tab_refresh()

		didRecentUpdate = False
		didMessagesUpdate = False

		if pageIndex == self.RECENT_TAB:
			didRecentUpdate = self._recentViews[self._selectedBackendId].update()
		elif pageIndex == self.MESSAGES_TAB:
			didMessagesUpdate = self._messagesViews[self._selectedBackendId].update()
		elif pageIndex == self.CONTACTS_TAB:
			self._contactsViews[self._selectedBackendId].update()
		elif pageIndex == self.ACCOUNT_TAB:
			self._accountViews[self._selectedBackendId].update()

		if didRecentUpdate or didMessagesUpdate:
			if self._ledHandler is not None:
				self._ledHandler.off()

	def _set_tab_refresh(self, *args):
		pageIndex = self._notebook.get_current_page()
		child = self._notebook.get_nth_page(pageIndex)
		self._notebook.get_tab_label(child).set_text("Refresh?")
		return False

	def _reset_tab_refresh(self, *args):
		pageIndex = self._notebook.get_current_page()
		child = self._notebook.get_nth_page(pageIndex)
		self._notebook.get_tab_label(child).set_text(self._originalCurrentLabels[pageIndex])
		return False

	def _on_tab_refresh(self, *args):
		self._refresh_active_tab()
		self._reset_tab_refresh()
		return False

	def _on_sms_clicked(self, number, message):
		assert number, "No number specified"
		assert message, "Empty message"
		try:
			loggedIn = self._phoneBackends[self._selectedBackendId].is_authed()
		except StandardError, e:
			loggedIn = False
			self._errorDisplay.push_exception()
			return

		if not loggedIn:
			self._errorDisplay.push_message(
				"Backend link with grandcentral is not working, please try again"
			)
			return

		dialed = False
		try:
			self._phoneBackends[self._selectedBackendId].send_sms(number, message)
			dialed = True
		except StandardError, e:
			self._errorDisplay.push_exception()
		except ValueError, e:
			self._errorDisplay.push_exception()

		if dialed:
			self._dialpads[self._selectedBackendId].clear()

	def _on_dial_clicked(self, number):
		assert number, "No number to call"
		try:
			loggedIn = self._phoneBackends[self._selectedBackendId].is_authed()
		except StandardError, e:
			loggedIn = False
			self._errorDisplay.push_exception()
			return

		if not loggedIn:
			self._errorDisplay.push_message(
				"Backend link with grandcentral is not working, please try again"
			)
			return

		dialed = False
		try:
			assert self._phoneBackends[self._selectedBackendId].get_callback_number() != "", "No callback number specified"
			self._phoneBackends[self._selectedBackendId].dial(number)
			dialed = True
		except StandardError, e:
			self._errorDisplay.push_exception()
		except ValueError, e:
			self._errorDisplay.push_exception()

		if dialed:
			self._dialpads[self._selectedBackendId].clear()

	def _on_menu_refresh(self, *args):
		self._refresh_active_tab()

	def _on_paste(self, *args):
		contents = self._clipboard.wait_for_text()
		self._dialpads[self._selectedBackendId].set_number(contents)

	def _on_about_activate(self, *args):
		dlg = gtk.AboutDialog()
		dlg.set_name(constants.__pretty_app_name__)
		dlg.set_version(constants.__version__)
		dlg.set_copyright("Copyright 2008 - LGPL")
		dlg.set_comments("Dialcentral is a touch screen enhanced interface to your GoogleVoice/Grandcentral account.  This application is not affiliated with Google in any way")
		dlg.set_website("http://gc-dialer.garage.maemo.org/")
		dlg.set_authors(["<z2n@merctech.com>", "Eric Warnke <ericew@gmail.com>", "Ed Page <edpage@byu.net>"])
		dlg.run()
		dlg.destroy()


def run_doctest():
	import doctest

	failureCount, testCount = doctest.testmod()
	if not failureCount:
		print "Tests Successful"
		sys.exit(0)
	else:
		sys.exit(1)


def run_dialpad():
	_lock_file = os.path.join(constants._data_path_, ".lock")
	#with gtk_toolbox.flock(_lock_file, 0):
	gtk.gdk.threads_init()

	if hildon is not None:
		gtk.set_application_name(constants.__pretty_app_name__)
	handle = Dialcentral()
	gtk.main()


class DummyOptions(object):

	def __init__(self):
		self.test = False


if __name__ == "__main__":
	if len(sys.argv) > 1:
		try:
			import optparse
		except ImportError:
			optparse = None

		if optparse is not None:
			parser = optparse.OptionParser()
			parser.add_option("-t", "--test", action="store_true", dest="test", help="Run tests")
			(commandOptions, commandArgs) = parser.parse_args()
	else:
		commandOptions = DummyOptions()
		commandArgs = []

	if commandOptions.test:
		run_doctest()
	else:
		run_dialpad()
