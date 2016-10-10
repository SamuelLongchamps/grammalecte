import sys
from os.path import join

from PySide.QtCore import QTranslator
from PySide.QtGui import QApplication

from grammalecte_frontend.qt.main_window import MainWindow


class ViewQt:
    """
    Main view of the application
    """

    QT_APPLICATION = QApplication(["Grammalecte"], QApplication.GuiClient)
    # TRANSLATOR = QTranslator()
    # i18n = join(project_root(), "i18n", "fr_CA")
    # TRANSLATOR.load(i18n)
    # QT_APPLICATION.installTranslator(TRANSLATOR)

    def __init__(self):
        self._main_window = MainWindow()

    def launch(self):
        """
        Launch the view (blocking call)
        """
        self._main_window.show()
        sys.exit(ViewQt.QT_APPLICATION.exec_())
