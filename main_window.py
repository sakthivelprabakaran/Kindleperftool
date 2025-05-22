# main_window.py
from PyQt5.QtWidgets import (QMainWindow, QToolBar, QTabWidget, QVBoxLayout,
                             QWidget, QApplication, QAction, QStatusBar,
                             QMessageBox, QFileDialog, QLabel)
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtCore import Qt, pyqtSlot, QTimer
from typing import Optional

# Local imports
from .widgets.stopwatch import StopwatchWidget
from .widgets.test_table import TestTableWidget
from .widgets.test_steps_viewer import TestStepsViewerWidget
from .widgets.history_view import HistoryViewWidget
from .widgets.notes_search import NotesSearchWidget
from .widgets.project_popup import ProjectPopup
from .utils.data_model import Session, TestCase
from .utils.file_manager import save_session, load_session, load_test_case_template, export_session_to_csv # Import export
from .utils.timer_utils import format_time # Useful for status bar


class MainWindow(QMainWindow):
    """Main window of the KindlePerfMate application."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KindlePerfMate")
        self.setGeometry(100, 100, 1200, 800) # Initial window size

        self.current_session: Optional[Session] = None
        self._current_session_filepath: Optional[str] = None
        self._unsaved_changes = False # Flag to track changes

        self.setup_ui()
        self.create_toolbar()
        self.connect_signals()
        self.setup_status_bar()

        # Set up event filter to capture global key presses (like spacebar)
        QApplication.instance().installEventFilter(self)

        self.check_unsaved_timer = QTimer(self)
        self.check_unsaved_timer.setInterval(5000) # Check every 5 seconds
        self.check_unsaved_timer.timeout.connect(self._check_for_unsaved_changes)
        self.check_unsaved_timer.start()

        self.new_project() # Start with a new project on launch

    def setup_ui(self):
        """Sets up the main window layout and widgets."""
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # Instantiate widgets
        self.stopwatch_widget = StopwatchWidget()
        self.test_table_widget = TestTableWidget()
        self.test_steps_viewer_widget = TestStepsViewerWidget()
        self.history_view_widget = HistoryViewWidget()
        self.notes_search_widget = NotesSearchWidget()

        # Add widgets as tabs
        self.tab_widget.addTab(self.stopwatch_widget, "Stopwatch")
        self.tab_widget.addTab(self.test_table_widget, "Test Data")
        self.tab_widget.addTab(self.test_steps_viewer_widget, "Test Steps")
        self.tab_widget.addTab(self.history_view_widget, "History")
        self.tab_widget.addTab(self.notes_search_widget, "Notes & Search")

    def create_toolbar(self):
        """Creates and populates the application toolbar."""
        toolbar = self.addToolBar("Main Toolbar")

        # Icons (Using built-in icons or placeholder text)
        # You should replace these with actual .png icons from assets/icons
        new_icon = QIcon.fromTheme("document-new", QIcon("assets/icons/new.png")) # Placeholder
        save_icon = QIcon.fromTheme("document-save", QIcon("assets/icons/save.png"))
        load_icon = QIcon.fromTheme("document-open", QIcon("assets/icons/load.png"))
        export_icon = QIcon.fromTheme("document-export", QIcon("assets/icons/export.png"))
        timer_icon = QIcon.fromTheme("chronometer", QIcon("assets/icons/timer.png")) # Adjust theme icon if needed

        # Actions
        new_action = QAction(new_icon, "&New Project", self)
        new_action.setStatusTip("Create a new performance testing session")
        new_action.triggered.connect(self.new_project)
        toolbar.addAction(new_action)

        save_action = QAction(save_icon, "&Save Session", self)
        save_action.setStatusTip("Save the current performance session")
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_session)
        toolbar.addAction(save_action)

        load_action = QAction(load_icon, "&Load History", self)
        load_action.setStatusTip("View and load past performance sessions")
        load_action.triggered.connect(lambda: self.tab_widget.setCurrentWidget(self.history_view_widget)) # Switch to history tab
        toolbar.addAction(load_action)

        toolbar.addSeparator()

        export_action = QAction(export_icon, "&Export Data", self)
        export_action.setStatusTip("Export current session data to CSV")
        export_action.triggered.connect(self.export_session)
        toolbar.addAction(export_action)

        toolbar.addSeparator()

        # Toggle Stopwatch/Timer Action (could potentially switch tabs or control the widget)
        # Let's make this action switch to the stopwatch tab for now.
        toggle_stopwatch_action = QAction(timer_icon, "&Stopwatch", self)
        toggle_stopwatch_action.setStatusTip("Switch to the Stopwatch tab")
        # toggle_stopwatch_action.setShortcut(Qt.Key_Space) # Handled by event filter
        toggle_stopwatch_action.triggered.connect(lambda: self.tab_widget.setCurrentWidget(self.stopwatch_widget))
        toolbar.addAction(toggle_stopwatch_action)

    def connect_signals(self):
        """Connects signals between widgets and Main Window methods."""
        # Connect Stopwatch to Table
        self.stopwatch_widget.iteration_saved.connect(self.test_table_widget.update_iteration_data)
        # Connect Table to Stopwatch and Steps Viewer
        self.test_table_widget.current_test_case_changed.connect(self.stopwatch_widget.update_current_test_case_info)
        self.test_table_widget.current_test_case_changed.connect(self.test_steps_viewer_widget.update_test_case_info)
        # Connect Stopwatch filter to Table filter
        self.stopwatch_widget.priority_filter_changed.connect(self.test_table_widget.apply_priority_filter)
        # Connect Table cell changes to update global notes (if TC notes changed) or set unsaved flag
        self.test_table_widget.cell_data_changed.connect(self._handle_data_changed)

        # Connect Notes widget changes to update session data and set unsaved flag
        self.notes_search_widget.global_notes_changed.connect(self._handle_global_notes_changed)

        # Connect History view requests to Main Window load method
        self.history_view_widget.load_session_requested.connect(self.load_session)

        # Connect signals that indicate changes requiring save
        self.test_table_widget.cell_data_changed.connect(self._set_unsaved_changes)
        self.notes_search_widget.global_notes_changed.connect(self._set_unsaved_changes)
        # Iteration saves also mean changes
        self.stopwatch_widget.iteration_saved.connect(self._set_unsaved_changes)
        # Add/Remove TC context menu actions (if implemented) should also call _set_unsaved_changes


    def setup_status_bar(self):
        """Sets up the status bar."""
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.status_label = QLabel("Ready")
        self.statusBar.addWidget(self.status_label)

        # Add info about current session (placeholder)
        self.session_info_label = QLabel("")
        self.statusBar.addPermanentWidget(self.session_info_label)


    def update_session_info_display(self):
         """Updates the status bar with current session details."""
         if self.current_session:
              info = f"Session: {self.current_session.week} | {self.current_session.device} | {self.current_session.build}"
              if self._current_session_filepath:
                   info += f" | Saved to: {os.path.basename(self._current_session_filepath)}"
              self.session_info_label.setText(info)
         else:
              self.session_info_label.setText("No active session")

    def _set_unsaved_changes(self):
        """Sets the internal flag indicating unsaved changes."""
        if not self._unsaved_changes:
            self._unsaved_changes = True
            print("Unsaved changes detected.")
            self.setWindowTitle("KindlePerfMate *") # Indicate unsaved changes

    def _clear_unsaved_changes(self):
        """Clears the internal flag indicating unsaved changes."""
        if self._unsaved_changes:
            self._unsaved_changes = False
            print("Unsaved changes cleared.")
            self.setWindowTitle("KindlePerfMate")

    def _check_for_unsaved_changes(self):
        """Periodically checks if the session data has been modified and updates the flag."""
        # This requires comparing the current state to a saved state or deep copy.
        # A simpler approach for now: The signals themselves set the flag.
        # This timer is useful for prompting before closing, not detecting *all* changes.
        # For now, we just print a message if the flag is set.
        if self._unsaved_changes:
            # print("Periodic check: Unsaved changes exist.")
            pass # The signal connections are responsible for setting _unsaved_changes


    def closeEvent(self, event):
        """Handles the window closing event, checks for unsaved changes."""
        if self._unsaved_changes:
            reply = QMessageBox.question(self, 'Save Changes',
                                         "You have unsaved changes. Do you want to save before quitting?",
                                         QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                                         QMessageBox.Save) # Default button

            if reply == QMessageBox.Save:
                if self.save_session(): # Try to save
                    event.accept() # Close if save was successful
                else:
                    event.ignore() # Don't close if save failed (e.g., user cancelled save dialog)
            elif reply == QMessageBox.Discard:
                event.accept() # Close without saving
            else: # Cancel
                event.ignore() # Don't close
        else:
            event.accept() # No changes, just close


    @pyqtSlot()
    def new_project(self):
        """Opens a popup for new project details and initializes a new session."""
        if self._unsaved_changes:
             reply = QMessageBox.question(self, 'Unsaved Changes',
                                          "Creating a new project will discard unsaved changes in the current session. Continue?",
                                          QMessageBox.Ok | QMessageBox.Cancel)
             if reply == QMessageBox.Cancel:
                  return # User cancelled

        popup = ProjectPopup(self)
        if popup.exec_() == ProjectPopup.Accepted:
            project_data = popup.get_data()
            print("New Project Data:", project_data)

            # Create a new session object
            new_session = Session(
                 week=project_data.get("week", ""),
                 device=project_data.get("device", ""),
                 build=project_data.get("build", ""),
                 priority_filter=project_data.get("priority_filter", "All")
            )

            # Load test cases based on the selected priority filter
            if new_session.priority_filter != "All":
                 # Load template only for the selected filter if not "All"
                 new_session.test_cases = load_test_case_template(new_session.priority_filter)
                 print(f"Loaded {len(new_session.test_cases)} test cases for priority filter '{new_session.priority_filter}'.")
            else:
                 # If "All", load templates for all known priorities (P0, P1, P2, P3, 750)
                 # This assumes you have template files for these. Adjust list as needed.
                 all_priorities = ["P0", "P1", "P2", "P3", "750"]
                 all_test_cases = []
                 for p in all_priorities:
                      all_test_cases.extend(load_test_case_template(p))
                 new_session.test_cases = all_test_cases
                 print(f"Loaded {len(new_session.test_cases)} test cases from all priorities for filter 'All'.")


            # Set the new session as the current one
            self.current_session = new_session
            self._current_session_filepath = None # New session is unsaved
            self._clear_unsaved_changes() # It's brand new, no changes yet

            # Update all widgets with the new session data
            self.load_session_data_into_widgets(self.current_session)

            self.update_session_info_display()
            self.statusBar.showMessage("New session created.", 2000)
        else:
            self.statusBar.showMessage("New session cancelled.", 2000)

    @pyqtSlot()
    def save_session(self) -> bool:
        """Saves the current session to a JSON file."""
        if self.current_session is None:
            QMessageBox.warning(self, "No Session", "No active session to save.")
            return False

        # If session hasn't been saved before, prompt for filename
        if self._current_session_filepath is None:
            # Suggest a default filename based on session details
            week = self.current_session.week.replace(" ", "_").replace("/", "-")
            device = self.current_session.device.replace(" ", "_").replace("/", "-")
            initial_filename = f"session_{week}_{device}.json"
            filepath, _ = QFileDialog.getSaveFileName(self, "Save Session",
                                                      initial_filename,
                                                      "Kindle PerfMate Sessions (*.json);;All Files (*)")
            if not filepath:
                self.statusBar.showMessage("Save cancelled.", 2000)
                return False # User cancelled save dialog

            self._current_session_filepath = filepath

        # Save the session data
        try:
            save_session(self.current_session, self._current_session_filepath)
            self._clear_unsaved_changes() # Mark as saved
            self.update_session_info_display()
            self.statusBar.showMessage(f"Session saved to {os.path.basename(self._current_session_filepath)}", 3000)
            return True # Save successful
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Error saving session:\n{e}")
            self.statusBar.showMessage("Error saving session.", 3000)
            return False # Save failed


    @pyqtSlot(str)
    def load_session(self, filepath: Optional[str] = None):
        """Loads a session from a JSON file."""
        if self._unsaved_changes:
            reply = QMessageBox.question(self, 'Unsaved Changes',
                                         "Loading a new session will discard unsaved changes. Continue?",
                                         QMessageBox.Ok | QMessageBox.Cancel)
            if reply == QMessageBox.Cancel:
                 self.statusBar.showMessage("Load cancelled.", 2000)
                 return # User cancelled

        if filepath is None: # If called from menu/button, not history list
             # Prompt user to select a file
             filepath, _ = QFileDialog.getOpenFileName(self, "Load Session",
                                                       "", # Default directory (can be set to SESSIONS_DIR)
                                                       "Kindle PerfMate Sessions (*.json);;All Files (*)")
             if not filepath:
                 self.statusBar.showMessage("Load cancelled.", 2000)
                 return # User cancelled load dialog


        loaded_session = load_session(filepath)

        if loaded_session:
            self.current_session = loaded_session
            self._current_session_filepath = filepath
            self._clear_unsaved_changes() # Loaded session is considered saved initially

            # Update all widgets with the loaded session data
            self.load_session_data_into_widgets(self.current_session)

            self.update_session_info_display()
            self.statusBar.showMessage(f"Session loaded from {os.path.basename(filepath)}", 3000)
            # Switch to Stopwatch tab after loading
            self.tab_widget.setCurrentWidget(self.stopwatch_widget)

        else:
            # Error message is handled by file_manager.load_session
            self.current_session = None # Clear current session on load failure
            self._current_session_filepath = None
            self._clear_unsaved_changes() # No session = no unsaved changes for previous (discarded) one
            self.load_session_data_into_widgets(None) # Clear widgets
            self.update_session_info_display()
            self.statusBar.showMessage("Failed to load session.", 3000)


    @pyqtSlot()
    def export_session(self):
        """Exports the current session data to a CSV file."""
        if self.current_session is None:
            QMessageBox.warning(self, "No Session", "No active session to export.")
            return

        # Suggest a default filename based on session details
        week = self.current_session.week.replace(" ", "_").replace("/", "-")
        device = self.current_session.device.replace(" ", "_").replace("/", "-")
        initial_filename = f"export_{week}_{device}.csv"

        filepath, _ = QFileDialog.getSaveFileName(self, "Export Session Data",
                                                  initial_filename,
                                                  "CSV Files (*.csv);;All Files (*)")

        if not filepath:
            self.statusBar.showMessage("Export cancelled.", 2000)
            return

        try:
            export_session_to_csv(self.current_session, filepath)
            self.statusBar.showMessage(f"Session exported successfully to {os.path.basename(filepath)}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Error exporting session:\n{e}")
            self.statusBar.showMessage("Error exporting session.", 3000)


    def load_session_data_into_widgets(self, session: Optional[Session]):
        """Distributes the session data to the relevant widgets."""
        # The TestTableWidget will be the primary source for filtering and selection
        self.test_table_widget.load_session_data(session)

        # Pass global notes to the Notes/Search widget
        if session:
             self.notes_search_widget.set_global_notes(session.global_notes)
             # Also tell the stopwatch what the default filter is
             self.stopwatch_widget.priority_filter_combo.setCurrentText(session.priority_filter)
        else:
             self.notes_search_widget.set_global_notes("")
             self.stopwatch_widget.priority_filter_combo.setCurrentText("All")


        # Trigger the initial selection update for Stopwatch and Steps Viewer
        # This happens automatically when test_table_widget.load_session_data
        # calls apply_priority_filter and potentially selects the first row.
        # If no rows are loaded, test_table_widget should emit
        # current_test_case_changed(-1, ...) to clear dependent widgets.


    @pyqtSlot(int, int, object)
    def _handle_data_changed(self, row_index_in_filtered_list: int, col_index: int, new_value: object):
         """Handles data changes originating from the TestTableWidget cell editing."""
         # This slot is mainly to catch changes that need to set the unsaved flag.
         # The TestTableWidget *already* updated the data model (self.session_data)
         # for Notes and Baseline changes.
         # We just need to ensure the unsaved flag is set.
         # Iteration data changes from stopwatch also set the flag via connect_signals.
         # print(f"Main Window: Data changed at filtered row {row_index_in_filtered_list}, col {col_index}. Setting unsaved flag.")
         self._set_unsaved_changes()

         # If the change was a Test Case Note, update the Notes/Search widget
         # (although NotesSearchWidget gets the full text when a session is loaded/saved)
         # A live update could be added here if needed.

    @pyqtSlot(str)
    def _handle_global_notes_changed(self, notes_text: str):
         """Handles changes to global notes from the Notes/Search widget."""
         if self.current_session:
              self.current_session.global_notes = notes_text
              # The NotesSearchWidget signal already sets the unsaved flag via connect_signals.
              # print(f"Main Window: Global notes updated in session data. Setting unsaved flag.")
         else:
              print("Warning: Global notes changed but no session is active.")


    # Implement event filter for global key presses
    def eventFilter(self, obj, event):
        """Filters events for the application."""
        if event.type() == event.KeyPress and event.key() == Qt.Key_Space:
            # Check if the stopwatch tab is currently active
            if self.tab_widget.currentWidget() == self.stopwatch_widget:
                 # Check if the event originated from a widget that shouldn't
                 # receive space (like a text editor) - but for simplicity,
                 # we'll just pass it directly to the stopwatch widget's handler
                 self.stopwatch_widget.handle_spacebar_press()
                 return True # Event was handled, don't propagate
            # elif self.tab_widget.currentWidget() == self.test_table_widget:
                 # Could add specific spacebar handling for the table (e.g., select next empty iter cell)
                 # For now, only handle in stopwatch tab
        return super().eventFilter(obj, event) # Let other events propagate