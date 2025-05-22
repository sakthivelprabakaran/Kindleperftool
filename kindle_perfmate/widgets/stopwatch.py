# widgets/stopwatch.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QLineEdit, QTextEdit, QComboBox,
                             QFormLayout, QFrame)
from PyQt5.QtCore import Qt, QTimer, QElapsedTimer, pyqtSignal, pyqtSlot
from typing import Optional
from ..utils.data_model import Iteration, TestCase
from ..utils.timer_utils import format_time

class StopwatchWidget(QWidget):
    """Widget containing the stopwatch, controls, and iteration inputs."""

    # Signal emitted when an iteration is confirmed
    # Emits: current_test_case_index (int), iteration_index (int), iteration_data (Iteration)
    iteration_saved = pyqtSignal(int, int, Iteration)
    # Signal emitted when the priority filter dropdown changes
    priority_filter_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.timer = QTimer(self)
        self.elapsed_timer = QElapsedTimer()
        self.is_running = False
        self._elapsed_ms: float = 0.0

        # We need to know which test case row and iteration we are currently on
        self._current_test_case_index: int = -1
        self._current_iteration_index: int = 0 # Iterations 0 to 4

        self._test_cases: list[TestCase] = [] # Reference to the list of test cases

        self.setup_ui()
        self.connect_signals()
        self.update_display(0) # Initialize display to 0

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Timer Display
        self.time_display = QLabel("00:00.000")
        self.time_display.setAlignment(Qt.AlignCenter)
        self.time_display.setStyleSheet("font-size: 60px; font-weight: bold;")
        layout.addWidget(self.time_display)

        # Controls
        control_layout = QHBoxLayout()
        self.start_stop_button = QPushButton("Start")
        self.start_stop_button.setCheckable(True) # Toggle behavior
        self.confirm_next_button = QPushButton("Confirm & Next")
        self.reset_button = QPushButton("Reset")
        self.reset_button.setEnabled(False) # Disabled until timer starts

        control_layout.addWidget(self.start_stop_button)
        control_layout.addWidget(self.confirm_next_button)
        control_layout.addWidget(self.reset_button)
        layout.addLayout(control_layout)

        # Current Test Case Info Display
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 10, 0, 10)
        self.current_test_case_label = QLabel("Current Test Case: --")
        self.current_iteration_label = QLabel("Iteration: 1 / 5")
        self.current_baseline_label = QLabel("Baseline: --")
        self.current_priority_label = QLabel("Priority: --") # Display *selected* priority for the TC

        info_layout.addWidget(self.current_test_case_label)
        info_layout.addWidget(self.current_iteration_label)
        info_layout.addWidget(self.current_baseline_label)
        info_layout.addWidget(self.current_priority_label)
        layout.addLayout(info_layout)


        # Inputs (Notes, Baseline, Priority Filter)
        input_frame = QFrame()
        input_frame.setFrameShape(QFrame.StyledPanel)
        input_layout = QFormLayout(input_frame)

        self.iteration_notes_input = QLineEdit()
        self.baseline_input = QLineEdit() # For entering/overriding baseline if needed manually
        self.priority_filter_combo = QComboBox() # This is the GLOBAL filter for the table
        self.priority_filter_combo.addItems(["All", "P0", "P1", "P2", "P3", "750"])
        self.priority_filter_combo.setCurrentText("All") # Default filter


        input_layout.addRow("Iteration Notes:", self.iteration_notes_input)
        # input_layout.addRow("Manual Baseline (ms):", self.baseline_input) # Keep this simple for now, use table baseline

        # Add the Priority Filter combo here as it affects the whole session/table view
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("View Priority:"))
        filter_layout.addWidget(self.priority_filter_combo)
        filter_layout.addStretch() # Push combo to the left
        layout.addLayout(filter_layout) # Add filter combo outside the frame


        # Add iteration notes input to the main layout for now, simpler structure
        layout.addRow(QLabel("Iteration Notes:"), self.iteration_notes_input)

        layout.addStretch() # Push everything to the top

    def connect_signals(self):
        self.timer.timeout.connect(self.update_time)
        self.start_stop_button.toggled.connect(self.toggle_timer)
        self.reset_button.clicked.connect(self.reset_timer)
        self.confirm_next_button.clicked.connect(self.confirm_and_next)
        self.priority_filter_combo.currentTextChanged.connect(self.priority_filter_changed.emit)

        # Setup Spacebar shortcut
        # Need to handle this in the main window or application event filter
        # For now, we'll rely on button clicks.

    def toggle_timer(self, checked):
        if checked: # Button is checked (Start)
            self.start_timer()
        else: # Button is unchecked (Stop)
            self.stop_timer()

    def start_timer(self):
        if not self.is_running:
            self.elapsed_timer.restart()
            self.timer.start(10) # Update every 10ms
            self.is_running = True
            self.start_stop_button.setText("Stop")
            self.start_stop_button.setChecked(True)
            self.reset_button.setEnabled(True)
            print("Stopwatch started")

    def stop_timer(self):
        if self.is_running:
            self.timer.stop()
            self._elapsed_ms = self.elapsed_timer.elapsed() # Get final elapsed time
            self.is_running = False
            self.start_stop_button.setText("Start")
            self.start_stop_button.setChecked(False) # Ensure it's unchecked visually
            print(f"Stopwatch stopped at {format_time(self._elapsed_ms)}")

    def reset_timer(self):
        self.stop_timer() # Ensure timer is stopped
        self._elapsed_ms = 0.0
        self.update_display(self._elapsed_ms)
        self.reset_button.setEnabled(False)
        print("Stopwatch reset")


    def update_time(self):
        """Updates the displayed time."""
        if self.is_running:
            self._elapsed_ms = self.elapsed_timer.elapsed()
            self.update_display(self._elapsed_ms)

    def update_display(self, milliseconds: float):
        """Formats and displays the time."""
        self.time_display.setText(format_time(milliseconds))

    def confirm_and_next(self):
        """Confirms the current time, saves iteration, and moves to the next."""
        if self._current_test_case_index == -1 or not self._test_cases:
            print("No test case selected or loaded.")
            return

        # Get the current test case object from the list
        if self._current_test_case_index >= len(self._test_cases):
             print(f"Error: Invalid current test case index {self._current_test_case_index}")
             return

        current_tc = self._test_cases[self._current_test_case_index]

        # Check if we are within the 5 iterations limit
        if self._current_iteration_index >= 5:
            print(f"Test Case '{current_tc.name}' already has 5 iterations. Cannot add more.")
            # Optionally, move to the next test case even if iterations are full
            self.move_to_next_test_case()
            return

        # 1. Stop the timer if running
        self.stop_timer()

        # 2. Get data
        iteration_time = self._elapsed_ms # Time is already captured by stop_timer
        iteration_notes = self.iteration_notes_input.text().strip()
        # Skipped state would need a checkbox

        # 3. Create or update the iteration data object
        # Ensure we have an Iteration object at the current index, create if needed
        while len(current_tc.iterations) <= self._current_iteration_index:
             current_tc.iterations.append(Iteration())

        # Update the specific iteration object
        current_tc.iterations[self._current_iteration_index].time_ms = iteration_time
        current_tc.iterations[self._current_iteration_index].notes = iteration_notes
        current_tc.iterations[self._current_iteration_index].skipped = False # Assuming Confirm is not skipped

        print(f"Confirmed iteration {self._current_iteration_index + 1} for '{current_tc.name}' with time {format_time(iteration_time)}")

        # 4. Emit signal to update the table
        self.iteration_saved.emit(
             self._current_test_case_index,
             self._current_iteration_index,
             current_tc.iterations[self._current_iteration_index] # Pass the updated iteration object
        )

        # 5. Reset stopwatch and inputs for the next iteration
        self.reset_timer()
        self.iteration_notes_input.clear()
        # Baseline input is not cleared, it's associated with the test case

        # 6. Advance to the next iteration or test case
        self._current_iteration_index += 1

        # If we finished all 5 iterations for the current TC, move to the next TC
        if self._current_iteration_index >= 5:
            print(f"Finished 5 iterations for '{current_tc.name}'. Moving to next test case.")
            self.move_to_next_test_case()
        else:
            # Still more iterations for the current TC
            self.update_current_info_display() # Update iteration number displayed

    def move_to_next_test_case(self):
        """Advances the currently active test case in the list."""
        next_index = -1
        # Find the index of the current TC object in the possibly filtered list
        try:
            # Need a way to find the *next visible* row in the table if filtering is applied.
            # This requires interaction with the TestTableWidget.
            # For now, let's just increment the index in the *full* list of test cases.
            # This might select a hidden row if filtering is active.
            # A better approach is to ask the TestTableWidget for the index of the next *visible* row.
            # Let's emit a signal asking the main window/table to advance.
            print("Requesting move to next test case via signal...")
            # We need a signal from here, or better, a slot that's called by the table when selection changes.
            # Let's rely on an external mechanism (like the table's selection change) to update us.
            # For now, we'll just reset internal state and wait for the table to tell us what's next.
            self._current_test_case_index = -1 # Invalidate current index
            self._current_iteration_index = 0 # Reset iteration counter for the new case
            self.update_current_info_display()
            # The TestTableWidget should listen for the end of 5 iterations and advance its selection.
            # When its selection changes, it calls `update_current_test_case_info`.

        except Exception as e:
            print(f"Error moving to next test case: {e}")
            # If we can't find the next, just reset state
            self._current_test_case_index = -1
            self._current_iteration_index = 0
            self.update_current_info_display()


    @pyqtSlot(int, TestCase, int)
    def update_current_test_case_info(self, row_index: int, test_case: TestCase, first_empty_iteration_index: int):
        """Slot to update the stopwatch widget based on the currently selected test case in the table."""
        self._current_test_case_index = row_index
        self._test_cases = [test_case] # Store just the current TC or pass the whole list?
                                      # Storing the whole list might be better if move_to_next_test_case
                                      # needs to know about other TCs. Let's update TestTable to pass the list.
        # Assume the TestTableWidget passes the *entire* list of test cases it's displaying (filtered or not)
        # And the *index* of the currently selected row *within that list*.
        # Let's refine the signal: `current_test_case_changed(list_of_test_cases, selected_index_in_list, first_empty_iteration)`
        # This requires a change in TestTableWidget. For now, simulate:
        self._test_cases = [test_case] # Just hold the one TC for display purposes
        self._current_test_case_index = 0 # Index within *this* temp list is 0
        self._current_iteration_index = first_empty_iteration_index # Tell stopwatch which iter to start at

        self.update_current_info_display()
        print(f"Stopwatch updated for TC: '{test_case.name}', starting iteration: {first_empty_iteration_index + 1}")


    def update_current_info_display(self):
        """Updates labels showing current TC name, iteration, baseline, priority."""
        if self._test_cases and self._current_test_case_index != -1 and self._current_test_case_index < len(self._test_cases):
            tc = self._test_cases[self._current_test_case_index]
            self.current_test_case_label.setText(f"Current Test Case: {tc.name}")
            # Display current iteration (1-based index) and total (5)
            self.current_iteration_label.setText(f"Iteration: {min(self._current_iteration_index, 5) + 1} / 5")
            self.current_baseline_label.setText(f"Baseline: {format_time(tc.baseline_ms)}")
            self.current_priority_label.setText(f"Priority: {tc.priority}")
            # Pre-fill notes if there are any for the current iteration
            if self._current_iteration_index < len(tc.iterations):
                 self.iteration_notes_input.setText(tc.iterations[self._current_iteration_index].notes)
            else:
                 self.iteration_notes_input.clear()
        else:
            self.current_test_case_label.setText("Current Test Case: --")
            self.current_iteration_label.setText("Iteration: -- / --")
            self.current_baseline_label.setText("Baseline: --")
            self.current_priority_label.setText("Priority: --")
            self.iteration_notes_input.clear()

    # Add a method to handle the spacebar press (called from main window's event filter)
    @pyqtSlot()
    def handle_spacebar_press(self):
        """Handles the spacebar shortcut to toggle the timer."""
        self.start_stop_button.toggle()
        print("Spacebar pressed (toggle timer)")


# Example Usage (for testing stopwatch widget)
if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication, QMainWindow
    import sys

    class MockTable: # Simulate the table widget
        def __init__(self):
            self.test_cases = [
                TestCase(name="TC1", steps=["Step A"], priority="P0", baseline_ms=600, iterations=[Iteration(), Iteration()]), # 2 iterations already
                TestCase(name="TC2", steps=["Step B"], priority="P1", baseline_ms=1500), # 0 iterations
                TestCase(name="TC3", steps=["Step C"], priority="P0", baseline_ms=800, iterations=[Iteration() for _ in range(5)]) # 5 iterations
            ]
            self._current_row = 0 # Simulate selected row

        def get_current_test_case_data(self) -> tuple[int, TestCase, int]:
             """Simulates getting data for the current row from the table."""
             if not self.test_cases: return -1, None, 0
             tc = self.test_cases[self._current_row]
             # Find the first empty iteration index
             first_empty_iter = next((i for i, iter in enumerate(tc.iterations) if iter.time_ms is None), len(tc.iterations))
             return self._current_row, tc, first_empty_iter

        def save_iteration(self, row_index, iter_index, iter_data):
             """Simulates saving data back to the table's data source."""
             print(f"MockTable: Received save data for row {row_index}, iter {iter_index}: {iter_data.time_ms}ms")
             if row_index < len(self.test_cases) and iter_index < len(self.test_cases[row_index].iterations):
                 self.test_cases[row_index].iterations[iter_index] = iter_data
                 print("MockTable: Data updated internally.")
                 # Simulate advancing row if 5 iterations are done
                 if iter_index == 4: # 0-indexed, so index 4 is the 5th iteration
                      self._current_row = (self._current_row + 1) % len(self.test_cases)
                      # In a real app, the table would emit a selection change signal now
                      print(f"MockTable: Row {row_index} complete. Advancing to row {self._current_row}")


    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Stopwatch Test")
            self.stopwatch = StopwatchWidget()
            self.setCentralWidget(self.stopwatch)

            # Simulate a table managing the data
            self.mock_table = MockTable()
            self.stopwatch.iteration_saved.connect(self.mock_table.save_iteration)

            # Simulate initial table selection (e.g., after loading session)
            row_index, tc_data, first_empty_iter = self.mock_table.get_current_test_case_data()
            self.stopwatch.update_current_test_case_info(row_index, tc_data, first_empty_iter)

            # Simulate changing selection to test next TC logic
            # After confirming the 5th iteration of TC1 (index 0),
            # the mock_table will advance _current_row to 1 (TC2).
            # A real table would then emit a signal. We'll simulate that here.
            # In a real app, the connection would be:
            # self.mock_table.currentRowChanged.connect(self._handle_table_row_change)
            # def _handle_table_row_change(self, new_row_index):
            #    _, tc_data, first_empty_iter = self.mock_table.get_current_test_case_data(new_row_index)
            #    self.stopwatch.update_current_test_case_info(new_row_index, tc_data, first_empty_iter)


    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())