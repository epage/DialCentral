import sys
import logging

from PyQt4 import QtCore
from PyQt4 import QtGui

import misc


_moduleLogger = logging.getLogger(__name__)


class QErrorLog(QtCore.QObject):

	messagePushed = QtCore.pyqtSignal()
	messagePopped = QtCore.pyqtSignal()

	def __init__(self):
		QtCore.QObject.__init__(self)
		self._messages = []

	def push_message(self, message):
		self._messages.append(message)
		self.messagePushed.emit()

	def push_exception(self):
		userMessage = str(sys.exc_info()[1])
		_moduleLogger.exception(userMessage)
		self.push_message(userMessage)

	def pop_message(self):
		del self._messages[0]
		self.messagePopped.emit()

	def peek_message(self):
		return self._messages[0]

	def __len__(self):
		return len(self._messages)


class ErrorDisplay(object):

	def __init__(self, errorLog):
		self._errorLog = errorLog
		self._errorLog.messagePushed.connect(self._on_message_pushed)
		self._errorLog.messagePopped.connect(self._on_message_popped)

		errorIcon = get_theme_icon(("dialog-error", "app_install_error", "gtk-dialog-error"))
		self._severityIcon = errorIcon.pixmap(32, 32)
		self._severityLabel = QtGui.QLabel()
		self._severityLabel.setPixmap(self._severityIcon)

		self._message = QtGui.QLabel()
		self._message.setText("Boo")

		closeIcon = get_theme_icon(("window-close", "general_close", "gtk-close"))
		self._closeLabel = QtGui.QPushButton(closeIcon, "")
		self._closeLabel.clicked.connect(self._on_close)

		self._controlLayout = QtGui.QHBoxLayout()
		self._controlLayout.addWidget(self._severityLabel)
		self._controlLayout.addWidget(self._message)
		self._controlLayout.addWidget(self._closeLabel)

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
		self._errorLog.pop_message()

	@QtCore.pyqtSlot()
	@misc.log_exception(_moduleLogger)
	def _on_message_pushed(self):
		if 1 <= len(self._errorLog) and self._widget.isHidden():
			self._message.setText(self._errorLog.peek_message())
			self._widget.show()

	@QtCore.pyqtSlot()
	@misc.log_exception(_moduleLogger)
	def _on_message_popped(self):
		if len(self._errorLog) == 0:
			self._message.setText("")
			self._widget.hide()
		else:
			self._message.setText(self._errorLog.peek_message())


class QHtmlDelegate(QtGui.QStyledItemDelegate):

	# @bug Doesn't show properly with dark themes (Maemo)

	def paint(self, painter, option, index):
		newOption = QtGui.QStyleOptionViewItemV4(option)
		self.initStyleOption(newOption, index)

		doc = QtGui.QTextDocument()
		doc.setHtml(newOption.text)
		doc.setTextWidth(newOption.rect.width())

		if newOption.widget is not None:
			style = newOption.widget.style()
		else:
			style = QtGui.QApplication.style()

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

