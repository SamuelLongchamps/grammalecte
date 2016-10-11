from PySide.QtGui import QMainWindow, QLabel, QAction, QPlainTextEdit, \
    QListWidget, QSplitter, QIcon, QTextDocument, QTextBlock, QTextCursor, \
    QTextCharFormat, QColor
from PySide.QtCore import Signal, QThread

from grammalecte_frontend.core.client import correct, KEY_GRAMMAR_ERROR, \
    KEY_PARAGRAPH, KEY_SPELLING_ERROR, correctWithThread
from grammalecte_frontend.qt.pyside_dynamic import loadUi
from grammalecte_frontend.utils import ui_filepath, resource_filepath


class MainWindow(QMainWindow):

    finished_correct = Signal(list)

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        loadUi(ui_filepath("mainwindow.ui"), self)
        self.setWindowIcon(QIcon(resource_filepath("icon.svg")))

        self.splitter = self.splitter
        """:type: QSplitter"""
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 1)

        self.plainTextEdit = self.plainTextEdit
        """:type: QPlainTextEdit"""

        self.descriptionLabel = self.descriptionLabel
        """:type: QLabel"""

        self.listWidget = self.listWidget
        """:type: QListWidget"""
        # noinspection PyUnresolvedReferences
        self.listWidget.currentRowChanged.connect(self.updateDescription)

        self.actionCorrect = self.actionCorrect
        """:type: QAction"""
        # noinspection PyUnresolvedReferences
        self.actionCorrect.triggered.connect(self.onCorrect)
        self.actionCorrect.setIcon(QIcon(resource_filepath("correct.svg")))

        self._currentCorrections = {}
        self._thread = None
        """:type: QThread"""

        self.finished_correct.connect(self.onFinishedCorrect)

        self._spellCheckFormat = QTextCharFormat()
        self._spellCheckFormat.setFontUnderline(True)
        self._spellCheckFormat.setUnderlineStyle(
            QTextCharFormat.SpellCheckUnderline)

        # Initialize corrector client
        correct("Initialization")

    def onFinishedCorrect(self, corrections):
        self.statusBar().showMessage("Correction done.", 3000)
        self.actionCorrect.setEnabled(True)
        self.updateView(corrections)

    def updateDescription(self, currentRow):
        if currentRow != -1:
            description = self._currentCorrections[currentRow]
        else:
            description = ""

        self.descriptionLabel.setText(description)

    def _correctCallback(self, corrections):
        if self._thread:
            self._thread.exit()
        self.finished_correct.emit(corrections)

    def onCorrect(self):
        self.statusBar().showMessage("Correcting text...")
        self.actionCorrect.setEnabled(False)
        self._thread = correctWithThread(self.plainTextEdit.toPlainText(),
                                         self._correctCallback)

    def _clearFormatting(self):
        doc = self.plainTextEdit.document()
        """:type: QTextDocument"""
        if doc.characterCount() > 0:
            cursor = QTextCursor(doc)
            cursor.setPosition(0)
            cursor.setPosition(doc.characterCount() - 1,
                               QTextCursor.KeepAnchor)
            cursor.setCharFormat(QTextCharFormat())

    def _addMistake(self, mistake, initialPos, cursor):
        cursor.setPosition(initialPos + mistake["nStart"])
        cursor.setPosition(initialPos + mistake["nEnd"],
                           QTextCursor.KeepAnchor)
        cursor.mergeCharFormat(self._spellCheckFormat)
        word = cursor.selectedText()
        self.listWidget.addItem(word)

    def updateView(self, corrections):
        row = 0
        self._currentCorrections.clear()
        self.listWidget.clear()

        # Clear formatting
        doc = self.plainTextEdit.document()
        """:type: QTextDocument"""
        self._clearFormatting()

        for paragraph in corrections:
            paragraphId = paragraph[KEY_PARAGRAPH]

            block = doc.findBlockByNumber(paragraphId)
            """:type: QTextBlock"""
            cursor = QTextCursor(block)
            initialPos = block.position()

            self._spellCheckFormat.setUnderlineColor(QColor(30, 150, 30))
            for ge in paragraph[KEY_GRAMMAR_ERROR]:
                self._addMistake(ge, initialPos, cursor)
                self._currentCorrections[row] = ge["sMessage"]
                row += 1

            self._spellCheckFormat.setUnderlineColor(QColor(150, 30, 30))
            for se in paragraph[KEY_SPELLING_ERROR]:
                self._addMistake(se, initialPos, cursor)
                self._currentCorrections[row] = "Le mot semble mal écrit."
                row += 1
