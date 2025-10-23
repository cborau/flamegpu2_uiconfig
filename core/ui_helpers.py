from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox


def show_quiet_message(parent, title: str, text: str, buttons: QMessageBox.StandardButton | QMessageBox.StandardButtons = QMessageBox.Ok) -> int:
    """Display a confirmation dialog without triggering the system alert sound."""
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(QMessageBox.NoIcon)
    box.setStandardButtons(buttons)
    box.setWindowModality(Qt.WindowModal)
    return box.exec()
