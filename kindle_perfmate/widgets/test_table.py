# widgets/test_table.py
from PyQt5.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView,
                             QAbstractItemView, QMenu, QApplication, QAction)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor
from typing import List, Optional

from ..utils.data_model import Session, TestCase, Iteration
from ..utils.timer_utils import format_time, calculate_average, calculate_spike

# Define colors for spike highlighting (adjust as needed)
SPIKE_COLOR_MINOR = QColor(255, 255, 150) # Light Yellow (e.g., 10-20% over baseline/avg)
SPIKE_COLOR_MAJOR = QColor(255, 150, 150) # Light Red (e.g., > 20% over baseline/avg)
SPIKE_THRESHOLD_MINOR = 10 # % over baseline/average
SPIKE_THRESHOLD_MAJOR = 20 # % over baseline/average


class TestTableWidget(QTableWidget):
    """Table widget to display and manage test cases and iterations."""

    # Signal emitted when the current test case selection changes
    # Emits: selected_row_index (int), test_case_data (TestCase), first_empty_iteration_index (int)
    current_test_case_changed = pyqtSignal(int, TestCase, int)
    # Signal emitted when cell data is changed (e.g., notes, baseline)
    # Emits: row_index (int), col_index (int), new_value (Any)
    cell_data_changed = pyqtSignal(int, int, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.session_data: Optional[Session] = None # Reference to the main session data
        self.filtered_test_cases: List[TestCase] = [] # The list currently displayed (after filter)
        self._current_filter = "All" # Store the active filter string

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        # Define columns: TC Name, Iter1..Iter5, Average, Baseline, TC Notes, Steps, Priority, Quip URL
        # Hide Steps, Priority, Quip URL columns in the table view initially, use other widgets to show
        self.setColumnCount(5 + 1 + 1 + 1 + 3) # 5 iters, Avg, Base, TC Notes, Steps, Priority, Quip
        headers = [
            "Test Case",
            "Iter 1", "Iter 2", "Iter 3", "Iter 4", "Iter 5",
            "Average", "Baseline", "Notes", # Test Case Notes
            "Steps", "Priority", "Quip URL" # Hidden columns
        ]
        self.setHorizontalHeaderLabels(headers)

        # Configure table appearance
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents) # Test Case Name column
        self.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents) # Baseline column
        self.horizontalHeader().setSectionResizeMode(8, QHeaderView.Stretch) # Notes column
        for i in range(1, 6): # Iteration columns
             self.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.verticalHeader().setVisible(False) # Hide row numbers

        # Configure selection behavior
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection) # Only one row can be selected at a time

        # Hide columns that will be displayed elsewhere
        self.setColumnHidden(9, True)  # Steps
        self.setColumnHidden(10, True) # Priority
        self.setColumnHidden(11, True) # Quip URL

        # Enable editing for notes and baseline
        self.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked | QAbstractItemView.AnyKeyPressed)

    def connect_signals(self):
        # Connect selection change to emit custom signal
        self.itemSelectionChanged.connect(self.handle_selection_change)
        # Connect cell change for direct editing
        self.cellChanged.connect(self.handle_cell_changed)

    def load_session_data(self, session: Session):
        """Loads test cases from a session into the table."""
        self.session_data = session
        # Apply the current filter after loading
        self.apply_priority_filter(self._current_filter)
        print(f"Test table loaded data for session: Week={session.week}, TCs={len(session.test_cases)}")

    def apply_priority_filter(self, priority: str):
        """Filters the table rows based on the selected priority."""
        self._current_filter = priority
        self.clearContents() # Clear existing rows
        self.setRowCount(0)

        if not self.session_data:
            self.filtered_test_cases = []
            print("No session data to filter.")
            return

        # Filter the list of test cases
        if priority == "All":
            self.filtered_test_cases = self.session_data.test_cases[:] # Copy the list
        else:
            self.filtered_test_cases = [tc for tc in self.session_data.test_cases if tc.priority == priority]

        # Populate the table with filtered data
        self.setRowCount(len(self.filtered_test_cases))
        for row_index, tc in enumerate(self.filtered_test_cases):
            self.insert_test_case_row(row_index, tc)

        print(f"Applied filter: '{priority}'. Displaying {len(self.filtered_test_cases)} test cases.")

        # Automatically select the first row if any exist
        if self.rowCount() > 0:
            self.selectRow(0)
        else:
            # If no rows, emit signal with None/invalid data to reset dependent widgets
            self.current_test_case_changed.emit(-1, TestCase(name=""), 0)


    def insert_test_case_row(self, row_index: int, tc: TestCase):
        """Populates a single row in the table with TestCase data."""
        # Temporarily block signals to prevent cellChanged from firing during population
        self.blockSignals(True)

        self.setItem(row_index, 0, QTableWidgetItem(tc.name)) # Test Case Name

        # Iteration times and notes
        for i in range(5):
            iter_col = i + 1
            iter_notes_col = 8 # Notes column is currently fixed at index 8
            iter_data = tc.iterations[i] if i < len(tc.iterations) else Iteration()

            # Iteration Time Cell
            time_item = QTableWidgetItem(format_time(iter_data.time_ms))
            time_item.setData(Qt.UserRole, iter_data.time_ms) # Store actual value
            time_item.setFlags(time_item.flags() & ~Qt.ItemIsEditable) # Make time cells non-editable
            if iter_data.skipped:
                 time_item.setBackground(QColor(200, 200, 200)) # Grey out skipped
            self.setItem(row_index, iter_col, time_item)

        self.update_row_calculations(row_index) # Calculate and display average and spike

        # Baseline
        baseline_item = QTableWidgetItem(format_time(tc.baseline_ms))
        baseline_item.setData(Qt.UserRole, tc.baseline_ms) # Store actual value
        self.setItem(row_index, 7, baseline_item) # Baseline column

        # Test Case Notes (make editable)
        notes_item = QTableWidgetItem(tc.test_notes)
        self.setItem(row_index, 8, notes_item) # Test Case Notes column

        # Hidden columns (Steps, Priority, Quip) - store data here but keep hidden
        self.setItem(row_index, 9, QTableWidgetItem("; ".join(tc.steps))) # Steps
        self.setItem(row_index, 10, QTableWidgetItem(tc.priority))       # Priority
        self.setItem(row_index, 11, QTableWidgetItem(tc.quip_url))       # Quip URL


        self.blockSignals(False) # Re-enable signals

    def update_row_calculations(self, row_index: int):
        """Calculates and updates the average and spike highlighting for a specific row."""
        # Get the corresponding TestCase object from the filtered list
        if row_index < 0 or row_index >= len(self.filtered_test_cases):
            print(f"Error: update_row_calculations called with invalid row index {row_index}")
            return

        tc = self.filtered_test_cases[row_index]

        # Calculate Average
        average_ms = calculate_average(tc.iterations)
        avg_item = QTableWidgetItem(format_time(average_ms))
        avg_item.setData(Qt.UserRole, average_ms) # Store actual value
        avg_item.setFlags(avg_item.flags() & ~Qt.ItemIsEditable) # Make average cell non-editable
        self.setItem(row_index, 6, avg_item) # Average column

        # Update spike highlighting for iteration cells (Iter 1-5)
        baseline_ms = tc.baseline_ms if tc.baseline_ms is not None else (average_ms if average_ms is not None else None) # Prefer baseline, then average
        for i in range(5):
            iter_col = i + 1
            iter_item = self.item(row_index, iter_col)
            if iter_item is None: continue # Should not happen if row was inserted correctly

            iter_data = tc.iterations[i] if i < len(tc.iterations) else Iteration()
            iter_ms = iter_data.time_ms

            # Reset background first
            iter_item.setBackground(self.palette().base().color()) # Default background

            if iter_data.skipped:
                 iter_item.setBackground(QColor(200, 200, 200)) # Grey out skipped
                 continue # No spike calculation for skipped

            spike_pct = calculate_spike(iter_ms, tc.baseline_ms, average_ms) # Use baseline first, then average
            if spike_pct is not None and spike_pct > 0:
                if spike_pct >= SPIKE_THRESHOLD_MAJOR:
                    iter_item.setBackground(SPIKE_COLOR_MAJOR)
                elif spike_pct >= SPIKE_THRESHOLD_MINOR:
                    iter_item.setBackground(SPIKE_COLOR_MINOR)


    @pyqtSlot(int, int, Iteration)
    def update_iteration_data(self, row_index_in_filtered_list: int, iteration_index: int, iteration_data: Iteration):
        """Slot to receive iteration data from stopwatch and update the table and data model."""
        # row_index_in_filtered_list is the visual row index in the table
        # We need to find the corresponding TestCase in the main self.session_data.test_cases list
        # This is crucial because the filtered list changes, but the underlying data model is constant.

        if self.session_data is None or row_index_in_filtered_list < 0 or row_index_in_filtered_list >= len(self.filtered_test_cases):
             print(f"Error: Cannot update iteration data. Invalid row index or no session loaded. Row: {row_index_in_filtered_list}, Iter: {iteration_index}")
             return

        # Get the TestCase from the *filtered* list using the row index
        tc_in_filtered_list = self.filtered_test_cases[row_index_in_filtered_list]

        # Find the *original* index of this TestCase in the full session data list
        original_row_index = -1
        if self.session_data: # Should not be None based on checks above
             try:
                # Find the index of the object reference itself
                original_row_index = self.session_data.test_cases.index(tc_in_filtered_list)
             except ValueError:
                print(f"Error: Could not find test case '{tc_in_filtered_list.name}' in original session data list.")
                return # Cannot update data model if TC not found

        if original_row_index == -1 or iteration_index < 0 or iteration_index >= 5:
             print(f"Error: Invalid iteration index or original row index found. Orig Index: {original_row_index}, Iter: {iteration_index}")
             return

        # Update the data in the actual Session object
        # Ensure the iterations list is long enough
        while len(self.session_data.test_cases[original_row_index].iterations) <= iteration_index:
            self.session_data.test_cases[original_row_index].iterations.append(Iteration())

        # Update the specific iteration object
        self.session_data.test_cases[original_row_index].iterations[iteration_index] = iteration_data
        print(f"Data model updated for TC: '{tc_in_filtered_list.name}', Iteration: {iteration_index + 1}")


        # Now update the table cell visually (in the filtered view)
        # Temporarily block signals to prevent handle_cell_changed from firing
        self.blockSignals(True)

        iter_col = iteration_index + 1
        time_item = self.item(row_index_in_filtered_list, iter_col)
        if time_item:
            time_item.setText(format_time(iteration_data.time_ms))
            time_item.setData(Qt.UserRole, iteration_data.time_ms)
            if iteration_data.skipped:
                 time_item.setBackground(QColor(200, 200, 200)) # Grey out skipped
            else:
                 time_item.setBackground(self.palette().base().color()) # Reset background if not skipped
        else:
            # This should not happen if the row exists, but as a fallback
            print(f"Warning: Could not find item at row {row_index_in_filtered_list}, col {iter_col} to update visually.")


        # Recalculate and update average and spike highlighting for this row
        self.update_row_calculations(row_index_in_filtered_list)

        self.blockSignals(False) # Re-enable signals


    def handle_selection_change(self):
        """Handles selection change and emits signal with current test case data."""
        selected_rows = self.selectedIndexes()
        if not selected_rows:
            # No row selected, emit signal with invalid data
            print("Table selection cleared.")
            self.current_test_case_changed.emit(-1, TestCase(name=""), 0)
            return

        # Get the row index of the first selected item (since SingleSelection mode)
        row_index = selected_rows[0].row()

        if row_index < 0 or row_index >= len(self.filtered_test_cases):
            print(f"Error: Invalid row index selected: {row_index}")
            # Emit signal with invalid data if something goes wrong
            self.current_test_case_changed.emit(-1, TestCase(name=""), 0)
            return

        # Get the corresponding TestCase object from the filtered list
        selected_tc = self.filtered_test_cases[row_index]

        # Find the first empty iteration index for this test case
        first_empty_iter = next((i for i, iter in enumerate(selected_tc.iterations) if iter.time_ms is None), len(selected_tc.iterations))

        print(f"Table selection changed to row {row_index}: '{selected_tc.name}', first empty iter: {first_empty_iter + 1}")

        # Emit signal with row index (in the filtered view), TestCase object, and first empty iteration index
        self.current_test_case_changed.emit(row_index, selected_tc, first_empty_iter)

    def handle_cell_changed(self, row: int, column: int):
         """Handles manual editing of cells (Notes, Baseline)."""
         # Temporarily block signals to prevent recursive calls if setText/setData is used below
         self.blockSignals(True)

         # Get the item that was changed
         item = self.item(row, column)
         if item is None:
             self.blockSignals(False)
             return

         new_value = item.text().strip()

         # Find the original test case object in the session data
         if self.session_data is None or row < 0 or row >= len(self.filtered_test_cases):
             print(f"Error handling cell change: Invalid row index or no session data. Row: {row}, Col: {column}")
             self.blockSignals(False)
             return

         tc_in_filtered_list = self.filtered_test_cases[row]
         original_row_index = -1
         try:
             original_row_index = self.session_data.test_cases.index(tc_in_filtered_list)
         except ValueError:
             print(f"Error handling cell change: Could not find test case '{tc_in_filtered_list.name}' in original session data.")
             self.blockSignals(False)
             return

         tc = self.session_data.test_cases[original_row_index]

         # Update the data model based on the column
         col_name = self.horizontalHeaderItem(column).text()

         if col_name == "Notes": # Test Case Notes
             tc.test_notes = new_value
             print(f"Updated Notes for '{tc.name}' to: {new_value}")
             # Emit signal that data changed, potentially needed by Notes/Search tab
             self.cell_data_changed.emit(original_row_index, column, new_value)

         elif col_name == "Baseline":
             try:
                 # Attempt to parse the new value as milliseconds (float)
                 # Handle potential 's' suffix or just raw number
                 if new_value.lower().endswith('s'):
                     ms_value = float(new_value[:-1]) * 1000
                 elif new_value: # Not empty
                     ms_value = float(new_value)
                 else: # Empty string means clearing baseline
                     ms_value = None

                 tc.baseline_ms = ms_value
                 print(f"Updated Baseline for '{tc.name}' to: {ms_value} ms")

                 # Reformat the cell text to ensure consistency (e.g., 1234.56ms becomes 1.235s)
                 item.setText(format_time(ms_value))
                 item.setData(Qt.UserRole, ms_value) # Store numeric value
                 self.update_row_calculations(row) # Recalculate spike highlighting based on new baseline

                 # Emit signal that data changed
                 self.cell_data_changed.emit(original_row_index, column, ms_value)

             except ValueError:
                 print(f"Invalid Baseline value entered: {new_value}. Must be a number.")
                 # Revert the cell text to the previous valid value or empty
                 # item.setText(format_time(tc.baseline_ms)) # Revert visually
                 # Don't emit signal if value is invalid


         # Add handling for iteration notes if they were in the table (they are in StopwatchWidget now)
         # elif col_name.startswith("Iter ") and col_name.endswith(" Notes"):
         #     iter_index = int(col_name.split(" ")[1]) - 1
         #     if iter_index < len(tc.iterations):
         #          tc.iterations[iter_index].notes = new_value
         #          print(f"Updated Iter {iter_index+1} Notes for '{tc.name}' to: {new_value}")
                  # Emit signal? Maybe only if Notes/Search tab needs it live


         self.blockSignals(False) # Re-enable signals


    # Method to get the currently selected test case object
    def get_current_test_case(self) -> Optional[TestCase]:
        selected_rows = self.selectedIndexes()
        if not selected_rows:
            return None
        row_index = selected_rows[0].row()
        if row_index < 0 or row_index >= len(self.filtered_test_cases):
            return None
        return self.filtered_test_cases[row_index]


    # Context menu for adding/removing rows (Optional but useful)
    # def contextMenuEvent(self, event):
    #     menu = QMenu(self)
    #     add_action = menu.addAction("Add New Test Case")
    #     remove_action = menu.addAction("Remove Selected Test Case")
    #     action = menu.exec_(self.mapToGlobal(event.pos()))
    #
    #     if action == add_action:
    #         self.add_new_test_case()
    #     elif action == remove_action:
    #         self.remove_selected_test_case()

    # def add_new_test_case(self):
    #      """Adds a new empty test case to the data model and table."""
    #      if self.session_data is None: return
    #      new_tc = TestCase(name="New Test Case", priority=self._current_filter)
    #      self.session_data.test_cases.append(new_tc)
    #      # Reapply filter to show the new TC if it matches the current filter
    #      self.apply_priority_filter(self._current_filter)
    #      # Select the new row? Need to find its index after filtering/sorting

    # def remove_selected_test_case(self):
    #     """Removes the selected test case from the data model and table."""
    #     selected_rows = self.selectedIndexes()
    #     if not selected_rows: return
    #     row_index_in_filtered_list = selected_rows[0].row()
    #
    #     if self.session_data is None or row_index_in_filtered_list < 0 or row_index_in_filtered_list >= len(self.filtered_test_cases):
    #         return
    #
    #     tc_to_remove = self.filtered_test_cases[row_index_in_filtered_list]
    #
    #     # Remove from the original session data list
    #     try:
    #         self.session_data.test_cases.remove(tc_to_remove)
    #         print(f"Removed test case '{tc_to_remove.name}' from session data.")
    #         # Remove from the table view
    #         self.removeRow(row_index_in_filtered_list)
    #         # Re-select the row that was next, or clear selection
    #         if self.rowCount() > 0:
    #              next_row_index = min(row_index_in_filtered_list, self.rowCount() - 1)
    #              self.selectRow(next_row_index)
    #         else:
    #              self.clearSelection()
    #
    #     except ValueError:
    #         print(f"Error removing test case '{tc_to_remove.name}': Not found in session data list.")


# Example Usage (for testing the table widget)
if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
    import sys
    from ..utils.data_model import Session, TestCase, Iteration
    from ..utils.file_manager import load_test_case_template # Assuming template file exists or will be created

    app = QApplication(sys.argv)

    class MainWindowMock(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Test Table Widget")
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)

            self.test_table = TestTableWidget()
            layout.addWidget(self.test_table)

            # Create a dummy session or load from a template
            dummy_session = Session(week="WkTest", device="MockDevice", build="MockBuild", priority_filter="P0")
            # Load some test cases
            dummy_session.test_cases = load_test_case_template("P0") + load_test_case_template("P1")

            # Add some dummy iteration data
            if len(dummy_session.test_cases) > 0:
                 tc1 = dummy_session.test_cases[0]
                 tc1.iterations[0] = Iteration(time_ms=1100.0, notes="Cold")
                 tc1.iterations[1] = Iteration(time_ms=950.0, notes="Warm")
                 tc1.iterations[2] = Iteration(time_ms=1020.0)
                 tc1.iterations[3] = Iteration(time_ms=800.0)
                 tc1.iterations[4] = Iteration(time_ms=2500.0, notes="Spike!")
                 tc1.baseline_ms = 1000.0
                 tc1.test_notes = "Test notes for TC1"

            if len(dummy_session.test_cases) > 1:
                 tc2 = dummy_session.test_cases[1]
                 tc2.iterations[0] = Iteration(time_ms=1600.0)
                 tc2.iterations[1] = Iteration(time_ms=1550.0)
                 tc2.iterations[2] = Iteration(time_ms=1480.0)
                 tc2.baseline_ms = 1500.0
                 tc2.test_notes = "Test notes for TC2"

            # Load the dummy session into the table
            self.test_table.load_session_data(dummy_session)

            # Simulate stopwatch sending an update
            # Get the original index of TC1 ("App Launch") in the full list
            tc1_orig_index = -1
            for i, tc in enumerate(dummy_session.test_cases):
                 if tc.name == "App Launch":
                      tc1_orig_index = i
                      break

            # Find the row index of TC1 in the *filtered* list (assuming P0 filter applied by default load)
            tc1_filtered_index = -1
            for i, tc in enumerate(self.test_table.filtered_test_cases):
                 if tc.name == "App Launch":
                      tc1_filtered_index = i
                      break

            if tc1_filtered_index != -1:
                 print(f"\nSimulating stopwatch updating TC1 ('App Launch', filtered row {tc1_filtered_index})...")
                 new_iter_data = Iteration(time_ms=990.0, notes="Another run")
                 # The stopwatch emits the row index *in its view*, which corresponds to the index in the filtered list
                 self.test_table.update_iteration_data(tc1_filtered_index, 2, new_iter_data) # Update 3rd iteration (index 2)

            # Simulate changing the filter
            print("\nSimulating changing filter to P1...")
            self.test_table.apply_priority_filter("P1")

            # Test selection change signal
            self.test_table.current_test_case_changed.connect(
                 lambda r, tc, i: print(f"Selection changed: Row {r}, TC '{tc.name}', First empty iter: {i}")
            )

    main_window = MainWindowMock()
    main_window.show()
    sys.exit(app.exec_())