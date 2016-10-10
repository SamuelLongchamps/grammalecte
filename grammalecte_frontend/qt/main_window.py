from PySide.QtGui import QMainWindow, QLabel, QAction, QPlainTextEdit, \
    QListWidget, QSplitter, QIcon
from PySide.QtCore import Signal, QThread

from grammalecte_frontend.core.client import correct, KEY_GRAMMAR_ERROR, \
    KEY_PARAGRAPH, KEY_SPELLING_ERROR, correctWithThread
from grammalecte_frontend.qt.pyside_dynamic import loadUi
from grammalecte_frontend.utils import ui_filepath, resource_filepath


class MainWindow(QMainWindow):

    finished_correct = Signal()

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
        self._currentText = ""
        self._thread = None
        """:type: QThread"""

        self.finished_correct.connect(self.onFinishedCorrect)

    def onFinishedCorrect(self):
        self.statusBar().showMessage("Correction done.", 3000)
        self.actionCorrect.setEnabled(True)

    def updateDescription(self, currentRow):
        if currentRow != -1:
            description = self._currentCorrections[currentRow]
        else:
            description = ""

        self.descriptionLabel.setText(description)

    def onCorrect(self):
        self.statusBar().showMessage("Correcting text...")
        self.actionCorrect.setEnabled(False)
        self._thread = correctWithThread(self.plainTextEdit.toPlainText(),
                                         self.updateCorrections)

    def _getWord(self, paragraph, start, end):
        return self._currentText[paragraph][start:end]

    def updateCorrections(self, corrections):
        if self._thread:
            self._thread.exit()
        self.finished_correct.emit()

        self._currentText = self.plainTextEdit.toPlainText().split("\n")
        row = 0
        self._currentCorrections.clear()
        self.listWidget.clear()

        for paragraph in corrections:
            paragraphId = paragraph[KEY_PARAGRAPH]
            for ge in paragraph[KEY_GRAMMAR_ERROR]:
                word = self._getWord(paragraphId, ge["nStart"], ge["nEnd"])
                self.listWidget.addItem(word)
                self._currentCorrections[row] = ge["sMessage"]
                row += 1

            for se in paragraph[KEY_SPELLING_ERROR]:
                word = self._getWord(paragraphId, se["nStart"], se["nEnd"])
                self.listWidget.addItem(word)
                self._currentCorrections[row] = "Ce mot semble mal écrit."
                row += 1
