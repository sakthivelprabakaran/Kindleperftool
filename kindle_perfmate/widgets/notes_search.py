# widgets/notes_search.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTextEdit,
                             QLineEdit, QHBoxLayout, QPushButton)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from typing import Optional

class NotesSearchWidget(QWidget):
    """Widget for global notes and potential search functionality."""

    # Signal emitted when global notes are changed
    # Emits: notes_text (str)
    global_notes_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.connect_signals()

        # Timer for debouncing notes changes (don't emit signal on every keystroke)
        self._notes_timer = QTimer(self)
        self._notes_timer.setInterval(500) # Wait 500ms after typing stops
        self._notes_timer.setSingleShot(True)
        self._notes_timer.timeout.connect(self._emit_notes_changed)


    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Global Notes Section
        notes_label = QLabel("Global Session Notes:")
        layout.addWidget(notes_label)

        self.global_notes_edit = QTextEdit()
        self.global_notes_edit.setPlaceholderText("Enter global notes for this session here...")
        layout.addWidget(self.global_notes_edit, 1) # Give it stretch factor

        # Search Section (Placeholder)
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search notes (WIP)...")
        self.search_button = QPushButton("Search")
        self.search_button.setEnabled(False) # Disable search button for now

        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        layout.addLayout(search_layout)

        layout.addStretch(0) # Push everything up slightly


    def connect_signals(self):
        # Connect text change, but debounce emission
        self.global_notes_edit.textChanged.connect(self._notes_timer.start)

        # Connect search button (placeholder)
        # self.search_button.clicked.connect(self.perform_search) # Not implemented yet

    def _emit_notes_changed(self):
         """Emits the global_notes_changed signal."""
         self.global_notes_changed.emit(self.global_notes_edit.toPlainText())
         # print("Global notes signal emitted.") # Debugging

    @pyqtSlot(str)
    def set_global_notes(self, notes: str):
        """Sets the text of the global notes editor."""
        # Block signals to avoid emitting textChanged when setting the text programmatically
        self.global_notes_edit.blockSignals(True)
        self.global_notes_edit.setText(notes)
        self.global_notes_edit.blockSignals(False)

    def get_global_notes(self) -> str:
        """Gets the current text from the global notes editor."""
        return self.global_notes_edit.toPlainText()

    # Placeholder for search functionality
    # def perform_search(self):
    #     query = self.search_input.text()
    #     print(f"Searching for: {query} (WIP)")
    #     # Implement search logic here - need access to session data or pass signal up


# Example Usage
if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication, QMainWindow
    import sys

    app = QApplication(sys.argv)

    class MainWindowMock(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Test Notes Search Widget")
            self.notes_search = NotesSearchWidget()
            self.setCentralWidget(self.notes_search)

            # Simulate loading notes
            self.notes_search.set_global_notes("Initial notes loaded from session.")

            # Connect signal to see changes
            self.notes_search.global_notes_changed.connect(lambda text: print(f"Global notes changed: {text[:50]}..."))


    main_window = MainWindowMock()
    main_window.show()
    sys.exit(app.exec_())