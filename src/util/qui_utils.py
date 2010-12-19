import sys
import contextlib
import logging

from PyQt4 import QtCore
from PyQt4 import QtGui

import misc


_moduleLogger = logging.getLogger(__name__)


@contextlib.contextmanager
def notify_error(log):
	try:
		yield
	except:
		log.push_exception()


class ErrorMessage(object):

	LEVEL_BUSY = "busy"
	LEVEL_INFO = "info"
	LEVEL_ERROR = "error"

	def __init__(self, message, level):
		self._message = message
		self._level = level

	@property
	def level(self):
		return self._level

	@property
	def message(self):
		return self._message


class QErrorLog(QtCore.QObject):

	messagePushed = QtCore.pyqtSignal()
	messagePopped = QtCore.pyqtSignal()

	def __init__(self):
		QtCore.QObject.__init__(self)
		self._messages = []

	def push_busy(self, message):
		_moduleLogger.info("Entering state: %s" % message)
		self._push_message(message, ErrorMessage.LEVEL_BUSY)

	def push_message(self, message):
		self._push_message(message, ErrorMessage.LEVEL_INFO)

	def push_error(self, message):
		self._push_message(message, ErrorMessage.LEVEL_ERROR)

	def push_exception(self):
		userMessage = str(sys.exc_info()[1])
		_moduleLogger.exception(userMessage)
		self.push_error(userMessage)

	def pop(self, message = None):
		if message is None:
			del self._messages[0]
		else:
			_moduleLogger.info("Exiting state: %s" % message)
			messageIndex = [
				i
				for (i, error) in enumerate(self._messages)
				if error.message == message
			]
			# Might be removed out of order
			if messageIndex:
				del self._messages[messageIndex[0]]
		self.messagePopped.emit()

	def peek_message(self):
		return self._messages[0]

	def _push_message(self, message, level):
		self._messages.append(ErrorMessage(message, level))
		self.messagePushed.emit()

	def __len__(self):
		return len(self._messages)


class ErrorDisplay(object):

	_SENTINEL_ICON = QtGui.QIcon()

	def __init__(self, errorLog):
		self._errorLog = errorLog
		self._errorLog.messagePushed.connect(self._on_message_pushed)
		self._errorLog.messagePopped.connect(self._on_message_popped)

		self._icons = {
			ErrorMessage.LEVEL_BUSY:
				get_theme_icon(
					#("process-working", "gtk-refresh")
					("gtk-refresh", )
				).pixmap(32, 32),
			ErrorMessage.LEVEL_INFO:
				get_theme_icon(
					("dialog-information", "general_notes", "gtk-info")
				).pixmap(32, 32),
			ErrorMessage.LEVEL_ERROR:
				get_theme_icon(
					("dialog-error", "app_install_error", "gtk-dialog-error")
				).pixmap(32, 32),
		}
		self._severityLabel = QtGui.QLabel()
		self._severityLabel.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

		self._message = QtGui.QLabel()
		self._message.setText("Boo")
		self._message.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
		self._message.setWordWrap(True)

		closeIcon = get_theme_icon(("window-close", "general_close", "gtk-close"), self._SENTINEL_ICON)
		if closeIcon is not self._SENTINEL_ICON:
			self._closeLabel = QtGui.QPushButton(closeIcon, "")
		else:
			self._closeLabel = QtGui.QPushButton("X")
		self._closeLabel.clicked.connect(self._on_close)

		self._controlLayout = QtGui.QHBoxLayout()
		self._controlLayout.addWidget(self._severityLabel, 1, QtCore.Qt.AlignCenter)
		self._controlLayout.addWidget(self._message, 1000)
		self._controlLayout.addWidget(self._closeLabel, 1, QtCore.Qt.AlignCenter)

		self._topLevelLayout = QtGui.QHBoxLayout()
		self._topLevelLayout.addLayout(self._controlLayout)
		self._widget = QtGui.QWidget()
		self._widget.setLayout(self._topLevelLayout)
		self._widget.hide()

	@property
	def toplevel(self):
		return self._widget

	@QtCore.pyqtSlot()
	@QtCore.pyqtSlot(bool)
	@misc.log_exception(_moduleLogger)
	def _on_close(self, checked = False):
		self._errorLog.pop()

	@QtCore.pyqtSlot()
	@misc.log_exception(_moduleLogger)
	def _on_message_pushed(self):
		if 1 <= len(self._errorLog) and self._widget.isHidden():
			error = self._errorLog.peek_message()
			self._message.setText(error.message)
			self._severityLabel.setPixmap(self._icons[error.level])
			self._widget.show()

	@QtCore.pyqtSlot()
	@misc.log_exception(_moduleLogger)
	def _on_message_popped(self):
		if len(self._errorLog) == 0:
			self._message.setText("")
			self._widget.hide()
		else:
			error = self._errorLog.peek_message()
			self._message.setText(error.message)
			self._severityLabel.setPixmap(self._icons[error.level])


class QHtmlDelegate(QtGui.QStyledItemDelegate):

	# @bug Not showing all of a message

	def paint(self, painter, option, index):
		newOption = QtGui.QStyleOptionViewItemV4(option)
		self.initStyleOption(newOption, index)
		if newOption.widget is not None:
			style = newOption.widget.style()
		else:
			style = QtGui.QApplication.style()

		doc = QtGui.QTextDocument()
		doc.setHtml(newOption.text)
		doc.setTextWidth(newOption.rect.width())

		newOption.text = ""
		style.drawControl(QtGui.QStyle.CE_ItemViewItem, newOption, painter)

		ctx = QtGui.QAbstractTextDocumentLayout.PaintContext()
		if newOption.state & QtGui.QStyle.State_Selected:
			ctx.palette.setColor(
				QtGui.QPalette.Text,
				newOption.palette.color(
					QtGui.QPalette.Active,
					QtGui.QPalette.HighlightedText
				)
			)
		else:
			ctx.palette.setColor(
				QtGui.QPalette.Text,
				newOption.palette.color(
					QtGui.QPalette.Active,
					QtGui.QPalette.Text
				)
			)

		textRect = style.subElementRect(QtGui.QStyle.SE_ItemViewItemText, newOption)
		painter.save()
		painter.translate(textRect.topLeft())
		painter.setClipRect(textRect.translated(-textRect.topLeft()))
		doc.documentLayout().draw(painter, ctx)
		painter.restore()

	def sizeHint(self, option, index):
		newOption = QtGui.QStyleOptionViewItemV4(option)
		self.initStyleOption(newOption, index)

		doc = QtGui.QTextDocument()
		doc.setHtml(newOption.text)
		doc.setTextWidth(newOption.rect.width())
		size = QtCore.QSize(doc.idealWidth(), doc.size().height())
		return size


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


def screen_orientation():
	geom = QtGui.QApplication.desktop().screenGeometry()
	if geom.width() <= geom.height():
		return QtCore.Qt.Vertical
	else:
		return QtCore.Qt.Horizontal


def _null_get_theme_icon(iconNames, fallback = None):
	icon = fallback if fallback is not None else QtGui.QIcon()
	return icon


def _newqt_get_theme_icon(iconNames, fallback = None):
	for iconName in iconNames:
		if QtGui.QIcon.hasThemeIcon(iconName):
			icon = QtGui.QIcon.fromTheme(iconName)
			break
	else:
		icon = fallback if fallback is not None else QtGui.QIcon()
	return icon


try:
	QtGui.QIcon.fromTheme
	get_theme_icon = _newqt_get_theme_icon
except AttributeError:
	get_theme_icon = _null_get_theme_icon

