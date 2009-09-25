#!/usr/bin/python2.5

"""
DialCentral - Front end for Google's GoogleVoice service.
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

@todo Add "login failed" and "attempting login" notifications
"""


from __future__ import with_statement

import sys
import gc
import os
import threading
import base64
import ConfigParser
import itertools
import logging

import gtk
import gtk.glade

import constants
import hildonize
import gtk_toolbox


def getmtime_nothrow(path):
	try:
		return os.path.getmtime(path)
	except Exception:
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
	GV_BACKEND = 2
	BACKENDS = (NULL_BACKEND, GV_BACKEND)

	def __init__(self):
		self._initDone = False
		self._connection = None
		self._osso = None
		self._clipboard = gtk.clipboard_get()

		self._credentials = ("", "")
		self._selectedBackendId = self.NULL_BACKEND
		self._defaultBackendId = self.GV_BACKEND
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

		self._isFullScreen = False
		self._app = hildonize.get_app_class()()
		self._window = hildonize.hildonize_window(self._app, self._window)
		hildonize.hildonize_text_entry(self._widgetTree.get_widget("usernameentry"))
		hildonize.hildonize_password_entry(self._widgetTree.get_widget("passwordentry"))

		for scrollingWidget in (
			'recent_scrolledwindow',
			'message_scrolledwindow',
			'contacts_scrolledwindow',
			"phoneSelectionMessages_scrolledwindow",
			"smsMessages_scrolledwindow",
		):
			hildonize.hildonize_scrollwindow(self._widgetTree.get_widget(scrollingWidget))
		for scrollingWidget in (
			"phonetypes_scrolledwindow",
			"smsMessage_scrolledEntry",
		):
			hildonize.hildonize_scrollwindow_with_viewport(self._widgetTree.get_widget(scrollingWidget))

		replacementButtons = [gtk.Button("Test")]
		menu = hildonize.hildonize_menu(
			self._window,
			self._widgetTree.get_widget("dialpad_menubar"),
			replacementButtons
		)

		self._window.connect("key-press-event", self._on_key_press)
		self._window.connect("window-state-event", self._on_window_state_change)
		if not hildonize.IS_HILDON_SUPPORTED:
			logging.warning("No hildonization support")

		hildonize.set_application_title(self._window, "%s" % constants.__pretty_app_name__)

		self._window.connect("destroy", self._on_close)
		self._window.set_default_size(800, 300)
		self._window.show_all()

		self._loginSink = gtk_toolbox.threaded_stage(
			gtk_toolbox.comap(
				self._attempt_login,
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
		# Barebones UI handlers
		try:
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
		except Exception, e:
			with gtk_toolbox.gtk_lock():
				self._errorDisplay.push_exception()

		# Setup maemo specifics
		try:
			try:
				import osso
			except (ImportError, OSError):
				osso = None
			self._osso = None
			if osso is not None:
				self._osso = osso.Context(constants.__app_name__, constants.__version__, False)
				device = osso.DeviceState(self._osso)
				device.set_device_state_callback(self._on_device_state_change, 0)
			else:
				logging.warning("No device state support")

			try:
				import alarm_handler
				self._alarmHandler = alarm_handler.AlarmHandler()
			except (ImportError, OSError):
				alarm_handler = None
			except Exception:
				with gtk_toolbox.gtk_lock():
					self._errorDisplay.push_exception()
				alarm_handler = None
				logging.warning("No notification support")
			if hildonize.IS_HILDON_SUPPORTED:
				try:
					import led_handler
					self._ledHandler = led_handler.LedHandler()
				except Exception, e:
					logging.exception('LED Handling failed: "%s"' % str(e))
					self._ledHandler = None
			else:
				self._ledHandler = None

			try:
				import conic
			except (ImportError, OSError):
				conic = None
			self._connection = None
			if conic is not None:
				self._connection = conic.Connection()
				self._connection.connect("connection-event", self._on_connection_change, constants.__app_magic__)
				self._connection.request_connection(conic.CONNECT_FLAG_NONE)
			else:
				logging.warning("No connection support")
		except Exception, e:
			with gtk_toolbox.gtk_lock():
				self._errorDisplay.push_exception()

		# Setup costly backends
		try:
			import gv_backend
			import file_backend
			import gv_views

			try:
				os.makedirs(constants._data_path_)
			except OSError, e:
				if e.errno != 17:
					raise
			gvCookiePath = os.path.join(constants._data_path_, "gv_cookies.txt")

			self._phoneBackends.update({
				self.GV_BACKEND: gv_backend.GVDialer(gvCookiePath),
			})
			with gtk_toolbox.gtk_lock():
				unifiedDialpad = gv_views.Dialpad(self._widgetTree, self._errorDisplay)
				self._dialpads.update({
					self.GV_BACKEND: unifiedDialpad,
				})
				self._accountViews.update({
					self.GV_BACKEND: gv_views.AccountInfo(
						self._widgetTree, self._phoneBackends[self.GV_BACKEND], self._alarmHandler, self._errorDisplay
					),
				})
				self._accountViews[self.GV_BACKEND].save_everything = self._save_settings
				self._recentViews.update({
					self.GV_BACKEND: gv_views.RecentCallsView(
						self._widgetTree, self._phoneBackends[self.GV_BACKEND], self._errorDisplay
					),
				})
				self._messagesViews.update({
					self.GV_BACKEND: gv_views.MessagesView(
						self._widgetTree, self._phoneBackends[self.GV_BACKEND], self._errorDisplay
					),
				})
				self._contactsViews.update({
					self.GV_BACKEND: gv_views.ContactsView(
						self._widgetTree, self._phoneBackends[self.GV_BACKEND], self._errorDisplay
					),
				})

			fsContactsPath = os.path.join(constants._data_path_, "contacts")
			fileBackend = file_backend.FilesystemAddressBookFactory(fsContactsPath)

			self._dialpads[self.GV_BACKEND].number_selected = self._select_action
			self._recentViews[self.GV_BACKEND].number_selected = self._select_action
			self._messagesViews[self.GV_BACKEND].number_selected = self._select_action
			self._contactsViews[self.GV_BACKEND].number_selected = self._select_action

			addressBooks = [
				self._phoneBackends[self.GV_BACKEND],
				fileBackend,
			]
			mergedBook = gv_views.MergedAddressBook(addressBooks, gv_views.MergedAddressBook.advanced_lastname_sorter)
			self._contactsViews[self.GV_BACKEND].append(mergedBook)
			self._contactsViews[self.GV_BACKEND].extend(addressBooks)
			self._contactsViews[self.GV_BACKEND].open_addressbook(*self._contactsViews[self.GV_BACKEND].get_addressbooks().next()[0][0:2])

			callbackMapping = {
				"on_paste": self._on_paste,
				"on_refresh": self._on_menu_refresh,
				"on_clearcookies_clicked": self._on_clearcookies_clicked,
				"on_about_activate": self._on_about_activate,
			}
			if hildonize.GTK_MENU_USED:
				self._widgetTree.signal_autoconnect(callbackMapping)
			self._notebook.connect("switch-page", self._on_notebook_switch_page)
			self._widgetTree.get_widget("clearcookies").connect("clicked", self._on_clearcookies_clicked)

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
		except Exception, e:
			with gtk_toolbox.gtk_lock():
				self._errorDisplay.push_exception()
		finally:
			self._spawn_attempt_login(2)

	def _spawn_attempt_login(self, *args):
		self._loginSink.send(args)

	def _attempt_login(self, numOfAttempts = 10, force = False):
		"""
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
				except Exception, e:
					logging.exception('Session refresh failed with the following message "%s"' % str(e))

			if not loggedIn:
				loggedIn, serviceId = self._login_by_user(numOfAttempts)

			with gtk_toolbox.gtk_lock():
				self._change_loggedin_status(serviceId)
				if loggedIn:
					hildonize.show_information_banner(self._window, "Logged In")
		except Exception, e:
			with gtk_toolbox.gtk_lock():
				self._errorDisplay.push_exception()

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
			logging.info("Logged into %r through cookies" % self._phoneBackends[self._defaultBackendId])
		return loggedIn

	def _login_by_settings(self):
		"""
		@note Thread agnostic
		"""
		username, password = self._credentials
		loggedIn = self._phoneBackends[self._defaultBackendId].login(username, password)
		if loggedIn:
			self._credentials = username, password
			logging.info("Logged into %r through settings" % self._phoneBackends[self._defaultBackendId])
		return loggedIn

	def _login_by_user(self, numOfAttempts):
		"""
		@note This must be run outside of the UI lock
		"""
		loggedIn, (username, password) = False, self._credentials
		tmpServiceId = self.GV_BACKEND
		for attemptCount in xrange(numOfAttempts):
			if loggedIn:
				break
			with gtk_toolbox.gtk_lock():
				credentials = self._credentialsDialog.request_credentials(
					defaultCredentials = self._credentials
				)
				if not self._phoneBackends[tmpServiceId].get_callback_number():
					# subtle reminder to the users to configure things
					self._notebook.set_current_page(self.ACCOUNT_TAB)
			username, password = credentials
			loggedIn = self._phoneBackends[tmpServiceId].login(username, password)

		if loggedIn:
			serviceId = tmpServiceId
			self._credentials = username, password
			logging.info("Logged into %r through user request" % self._phoneBackends[serviceId])
		else:
			serviceId = self.NULL_BACKEND
			self._notebook.set_current_page(self.ACCOUNT_TAB)

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

		self._selectedBackendId = newStatus

		self._accountViews[self._selectedBackendId].update()
		self._refresh_active_tab()

	def load_settings(self, config):
		"""
		@note UI Thread
		"""
		try:
			self._defaultBackendId = config.getint(constants.__pretty_app_name__, "active")
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
			logging.exception(
				"Settings file %s is missing section %s" % (
					constants._user_settings_,
					e.section,
				),
			)
		except ConfigParser.NoSectionError, e:
			logging.exception(
				"Settings file %s is missing section %s" % (
					constants._user_settings_,
					e.section,
				),
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
				logging.exception(
					"Settings file %s is missing section %s" % (
						constants._user_settings_,
						e.section,
					),
				)
			except ConfigParser.NoSectionError, e:
				logging.exception(
					"Settings file %s is missing section %s" % (
						constants._user_settings_,
						e.section,
					),
				)

		try:
			previousOrientation = config.getint(constants.__pretty_app_name__, "orientation")
			if previousOrientation == gtk.ORIENTATION_HORIZONTAL:
				hildonize.window_to_landscape(self._window)
			elif previousOrientation == gtk.ORIENTATION_VERTICAL:
				hildonize.window_to_portrait(self._window)
		except ConfigParser.NoOptionError, e:
			logging.exception(
				"Settings file %s is missing section %s" % (
					constants._user_settings_,
					e.section,
				),
			)
		except ConfigParser.NoSectionError, e:
			logging.exception(
				"Settings file %s is missing section %s" % (
					constants._user_settings_,
					e.section,
				),
			)

	def save_settings(self, config):
		"""
		@note Thread Agnostic
		"""
		config.add_section(constants.__pretty_app_name__)
		config.set(constants.__pretty_app_name__, "active", str(self._selectedBackendId))
		config.set(constants.__pretty_app_name__, "orientation", str(int(gtk_toolbox.get_screen_orientation())))
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
		try:
			if memory_low:
				for backendId in self.BACKENDS:
					self._phoneBackends[backendId].clear_caches()
				self._contactsViews[self._selectedBackendId].clear_caches()
				gc.collect()

			if save_unsaved_data or shutdown:
				self._save_settings()
		except Exception, e:
			self._errorDisplay.push_exception()

	def _on_connection_change(self, connection, event, magicIdentifier):
		"""
		@note Hildon specific
		"""
		try:
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
		except Exception, e:
			self._errorDisplay.push_exception()

	def _on_window_state_change(self, widget, event, *args):
		"""
		@note Hildon specific
		"""
		try:
			if event.new_window_state & gtk.gdk.WINDOW_STATE_FULLSCREEN:
				self._isFullScreen = True
			else:
				self._isFullScreen = False
		except Exception, e:
			self._errorDisplay.push_exception()

	def _on_key_press(self, widget, event, *args):
		"""
		@note Hildon specific
		"""
		try:
			if (
				event.keyval == gtk.keysyms.F6 or
				event.keyval == gtk.keysyms.Return and event.get_state() & gtk.gdk.CONTROL_MASK
			):
				if self._isFullScreen:
					self._window.unfullscreen()
				else:
					self._window.fullscreen()
		except Exception, e:
			self._errorDisplay.push_exception()

	def _on_clearcookies_clicked(self, *args):
		try:
			self._phoneBackends[self._selectedBackendId].logout()
			self._accountViews[self._selectedBackendId].clear()
			self._recentViews[self._selectedBackendId].clear()
			self._messagesViews[self._selectedBackendId].clear()
			self._contactsViews[self._selectedBackendId].clear()
			self._change_loggedin_status(self.NULL_BACKEND)

			self._spawn_attempt_login(2, True)
		except Exception, e:
			self._errorDisplay.push_exception()

	def _on_notebook_switch_page(self, notebook, page, pageIndex):
		try:
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
		except Exception, e:
			self._errorDisplay.push_exception()

	def _set_tab_refresh(self, *args):
		try:
			pageIndex = self._notebook.get_current_page()
			child = self._notebook.get_nth_page(pageIndex)
			self._notebook.get_tab_label(child).set_text("Refresh?")
		except Exception, e:
			self._errorDisplay.push_exception()
		return False

	def _reset_tab_refresh(self, *args):
		try:
			pageIndex = self._notebook.get_current_page()
			child = self._notebook.get_nth_page(pageIndex)
			self._notebook.get_tab_label(child).set_text(self._originalCurrentLabels[pageIndex])
		except Exception, e:
			self._errorDisplay.push_exception()
		return False

	def _on_tab_refresh(self, *args):
		try:
			self._refresh_active_tab()
			self._reset_tab_refresh()
		except Exception, e:
			self._errorDisplay.push_exception()
		return False

	def _on_sms_clicked(self, number, message):
		try:
			assert number, "No number specified"
			assert message, "Empty message"
			try:
				loggedIn = self._phoneBackends[self._selectedBackendId].is_authed()
			except Exception, e:
				loggedIn = False
				self._errorDisplay.push_exception()
				return

			if not loggedIn:
				self._errorDisplay.push_message(
					"Backend link with GoogleVoice is not working, please try again"
				)
				return

			dialed = False
			try:
				self._phoneBackends[self._selectedBackendId].send_sms(number, message)
				hildonize.show_information_banner(self._window, "Sending to %s" % number)
				dialed = True
			except Exception, e:
				self._errorDisplay.push_exception()

			if dialed:
				self._dialpads[self._selectedBackendId].clear()
		except Exception, e:
			self._errorDisplay.push_exception()

	def _on_dial_clicked(self, number):
		try:
			assert number, "No number to call"
			try:
				loggedIn = self._phoneBackends[self._selectedBackendId].is_authed()
			except Exception, e:
				loggedIn = False
				self._errorDisplay.push_exception()
				return

			if not loggedIn:
				self._errorDisplay.push_message(
					"Backend link with GoogleVoice is not working, please try again"
				)
				return

			dialed = False
			try:
				assert self._phoneBackends[self._selectedBackendId].get_callback_number() != "", "No callback number specified"
				self._phoneBackends[self._selectedBackendId].dial(number)
				hildonize.show_information_banner(self._window, "Calling %s" % number)
				dialed = True
			except Exception, e:
				self._errorDisplay.push_exception()

			if dialed:
				self._dialpads[self._selectedBackendId].clear()
		except Exception, e:
			self._errorDisplay.push_exception()

	def _on_menu_refresh(self, *args):
		try:
			self._refresh_active_tab()
		except Exception, e:
			self._errorDisplay.push_exception()

	def _on_paste(self, *args):
		try:
			contents = self._clipboard.wait_for_text()
			if contents is not None:
				self._dialpads[self._selectedBackendId].set_number(contents)
		except Exception, e:
			self._errorDisplay.push_exception()

	def _on_about_activate(self, *args):
		try:
			dlg = gtk.AboutDialog()
			dlg.set_name(constants.__pretty_app_name__)
			dlg.set_version("%s-%d" % (constants.__version__, constants.__build__))
			dlg.set_copyright("Copyright 2008 - LGPL")
			dlg.set_comments("Dialcentral is a touch screen enhanced interface to your GoogleVoice account.  This application is not affiliated with Google in any way")
			dlg.set_website("http://gc-dialer.garage.maemo.org/")
			dlg.set_authors(["<z2n@merctech.com>", "Eric Warnke <ericew@gmail.com>", "Ed Page <edpage@byu.net>"])
			dlg.run()
			dlg.destroy()
		except Exception, e:
			self._errorDisplay.push_exception()


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

	if hildonize.IS_HILDON_SUPPORTED:
		gtk.set_application_name(constants.__pretty_app_name__)
	handle = Dialcentral()
	gtk.main()


class DummyOptions(object):

	def __init__(self):
		self.test = False


if __name__ == "__main__":
	logging.basicConfig(level=logging.DEBUG)
	try:
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
	finally:
		logging.shutdown()
