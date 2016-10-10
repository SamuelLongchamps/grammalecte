import os
import sys


def project_root():
    if getattr(sys, 'frozen', False):
        # If the app is bundled, get the directory (using PyInstaller)
        return sys._MEIPASS
    else:
        # Support both cases if the file was run directly or by the module
        # folder
        return os.path.dirname(__file__) if __file__[-3:] == ".py" else __file__


def ui_filepath(ui_filename):
    """
    :param ui_filename: Filename of the ui file
    :return: Path relative to this project's root as a string of the ui file
    """
    return os.path.join(project_root(), "ui", ui_filename)


def resource_filepath(resource_filename):
    """
    :param resource_filename: Filename of the resource file
    :return: Path relative to this project's root as a string of the ui file
    """
    return os.path.join(project_root(), "res", resource_filename)
