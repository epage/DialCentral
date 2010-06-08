from PyQt4 import QtCore


def _null_set_stackable(window, isStackable):
	pass


def _maemo_set_stackable(window, isStackable):
	window.setAttribute(QtCore.Qt.WA_Maemo5StackedWindow, isStackable)


try:
	QtCore.Qt.WA_Maemo5StackedWindow
	set_stackable = _maemo_set_stackable
except AttributeError:
	set_stackable = _null_set_stackable


def _null_set_autorient(window, isStackable):
	pass


def _maemo_set_autorient(window, isStackable):
	window.setAttribute(QtCore.Qt.WA_Maemo5StackedWindow, isStackable)


try:
	QtCore.Qt.WA_Maemo5AutoOrientation
	set_autorient = _maemo_set_autorient
except AttributeError:
	set_autorient = _null_set_autorient


def _null_set_landscape(window, isStackable):
	pass


def _maemo_set_landscape(window, isStackable):
	window.setAttribute(QtCore.Qt.WA_Maemo5StackedWindow, isStackable)


try:
	QtCore.Qt.WA_Maemo5LandscapeOrientation
	set_landscape = _maemo_set_landscape
except AttributeError:
	set_landscape = _null_set_landscape


def _null_set_portrait(window, isStackable):
	pass


def _maemo_set_portrait(window, isStackable):
	window.setAttribute(QtCore.Qt.WA_Maemo5StackedWindow, isStackable)


try:
	QtCore.Qt.WA_Maemo5PortraitOrientation
	set_portrait = _maemo_set_portrait
except AttributeError:
	set_portrait = _null_set_portrait


def _null_show_progress_indicator(window, isStackable):
	pass


def _maemo_show_progress_indicator(window, isStackable):
	window.setAttribute(QtCore.Qt.WA_Maemo5StackedWindow, isStackable)


try:
	QtCore.Qt.WA_Maemo5ShowProgressIndicator
	show_progress_indicator = _maemo_show_progress_indicator
except AttributeError:
	show_progress_indicator = _null_show_progress_indicator


def _null_mark_numbers_preferred(widget):
	pass


def _newqt_mark_numbers_preferred(widget):
	widget.setInputMethodHints(QtCore.Qt.ImhPreferNumbers)


try:
	QtCore.Qt.ImhPreferNumbers
	mark_numbers_preferred = _newqt_mark_numbers_preferred
except AttributeError:
	mark_numbers_preferred = _null_mark_numbers_preferred
