# widgets/history_view.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QListWidget,
                             QPushButton, QHBoxLayout, QFileDialog)
from PyQt5.QtCore import Qt, pyqtSignal
from typing import List, Dict, Any

from ..utils.file_manager import list_sessions # Assuming file_manager exists

class HistoryViewWidget(QWidget):
    """Widget to view and load past sessions."""

    # Signal emitted when a session load is requested
    # Emits: filepath (str)
    load_session_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.connect_signals()
        self.load_session_list() # Load list when created

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        label = QLabel("Saved Sessions:")
        layout.addWidget(label)

        self.session_list_widget = QListWidget()
        layout.addWidget(self.session_list_widget)

        button_layout = QHBoxLayout()
        self.load_button = QPushButton("Load Selected Session")
        self.export_button = QPushButton("Export Selected Session") # Could add Export here too
        button_layout.addWidget(self.load_button)
        button_layout.addWidget(self.export_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Update button states based on selection
        self.load_button.setEnabled(False)
        self.export_button.setEnabled(False)


    def connect_signals(self):
        self.session_list_widget.itemSelectionChanged.connect(self.update_button_states)
        self.session_list_widget.itemDoubleClicked.connect(self.handle_double_click)
        self.load_button.clicked.connect(self.load_selected_session)
        # self.export_button.clicked.connect(self.export_selected_session) # Implement Export if needed here

    def load_session_list(self):
        """Clears the list and populates it with available sessions."""
        self.session_list_widget.clear()
        self.session_files_info = list_sessions() # Store the info dicts

        if not self.session_files_info:
            self.session_list_widget.addItem("No sessions found.")
            return

        for info in self.session_files_info:
            # Format string for display
            display_text = (f"Week: {info.get('week', 'N/A')}, "
                            f"Device: {info.get('device', 'N/A')}, "
                            f"Build: {info.get('build', 'N/A')} "
                            f"({info.get('start_time', 'N/A').split('T')[0]})") # Show date
            item = QListWidgetItem(display_text)
            # Store the full info dictionary with the item
            item.setData(Qt.UserRole, info)
            self.session_list_widget.addItem(item)

        self.update_button_states() # Update buttons based on the (initially empty) selection

    def update_button_states(self):
        """Enables/disables buttons based on whether an item is selected."""
        has_selection = len(self.session_list_widget.selectedItems()) > 0
        self.load_button.setEnabled(has_selection)
        self.export_button.setEnabled(has_selection)


    def get_selected_session_info(self) -> Optional[Dict[str, Any]]:
        """Gets the info dictionary for the currently selected session."""
        selected_items = self.session_list_widget.selectedItems()
        if not selected_items:
            return None
        # Get the data stored with the item
        return selected_items[0].data(Qt.UserRole)


    def handle_double_click(self, item: QListWidgetItem):
         """Handle double-click to load the session."""
         self.load_selected_session()

    def load_selected_session(self):
        """Emits a signal requesting to load the selected session file."""
        info = self.get_selected_session_info()
        if info:
            filepath = info.get('filepath')
            if filepath:
                 print(f"Load requested for: {filepath}")
                 self.load_session_requested.emit(filepath)
            else:
                 print("Error: Could not get filepath for selected session.")
        else:
            print("No session selected to load.")

    # Optional: Add export functionality specific to the history view
    # def export_selected_session(self):
    #      info = self.get_selected_session_info()
    #      if info:
    #           filepath_to_load = info.get('filepath')
    #           if filepath_to_load:
    #                # Need to load the session first (or rely on main window having it)
    #                # A simpler approach might be to handle export entirely in MainWindow
    #                # where the current session is already loaded.
    #                # If implementing here, load the session then prompt for export location.
    #                print(f"Export requested for: {filepath_to_load}")
    #                # For now, let's assume MainWindow handles export of the *current* session
    #                # and the user loads the history item they want to export first.
    #                print("Export from History View not yet implemented. Load the session first and use the main export button.")


# Example Usage
if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication, QMainWindow
    import sys
    import os
    # Need to create dummy session files for listing
    from ..utils.data_model import Session, TestCase
    from ..utils.file_manager import save_session, SESSIONS_DIR

    # Create some dummy sessions if none exist
    if not os.listdir(SESSIONS_DIR):
         print("Creating dummy sessions for history view test...")
         s1 = Session(week="Wk40", device="PW5", build="14.5", test_cases=[TestCase(name="TC A")])
         save_session(s1, "session_dummy_w40.json")
         s2 = Session(week="Wk41", device="Basic", build="14.6", test_cases=[TestCase(name="TC B"), TestCase(name="TC C")])
         save_session(s2, "session_dummy_w41.json")
         print("Dummy sessions created in:", SESSIONS_DIR)


    app = QApplication(sys.argv)

    class MainWindowMock(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Test History View")
            self.history_view = HistoryViewWidget()
            self.setCentralWidget(self.history_view)

            # Connect the signal
            self.history_view.load_session_requested.connect(self.handle_load_request)

        def handle_load_request(self, filepath):
            print(f"MainWindowMock received load request for: {filepath}")
            # In a real app, you would call file_manager.load_session(filepath)
            # and then populate the main window and other widgets.
            print("(Simulating loading...)")

    main_window = MainWindowMock()
    main_window.show()
    sys.exit(app.exec_())