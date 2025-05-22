# widgets/test_steps_viewer.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTextEdit,
                             QListWidget, QListWidgetItem, QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSlot
from typing import Optional

from ..utils.data_model import TestCase

class TestStepsViewerWidget(QWidget):
    """Widget to display steps and details for the currently selected test case."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_test_case: Optional[TestCase] = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.name_label = QLabel("Select a Test Case")
        self.name_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(self.name_label)

        # Frame for details
        details_frame = QFrame()
        details_frame.setFrameShape(QFrame.StyledPanel)
        details_layout = QVBoxLayout(details_frame)

        self.baseline_label = QLabel("Baseline: --")
        self.priority_label = QLabel("Priority: --")
        self.quip_label = QLabel("Quip URL: --")
        self.quip_label.setTextFormat(Qt.RichText) # Allow rich text (for links)
        self.quip_label.setOpenExternalLinks(True) # Open links externally


        details_layout.addWidget(self.baseline_label)
        details_layout.addWidget(self.priority_label)
        details_layout.addWidget(self.quip_label)
        layout.addWidget(details_frame)


        # Steps list
        steps_label = QLabel("Steps:")
        layout.addWidget(steps_label)

        self.steps_list = QListWidget()
        self.steps_list.setSelectionMode(QListWidget.NoSelection) # Not selectable
        self.steps_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.steps_list)

        # Test Case Specific Notes
        notes_label = QLabel("Test Case Notes:")
        layout.addWidget(notes_label)
        self.notes_viewer = QTextEdit()
        self.notes_viewer.setReadOnly(True) # Read-only view here, editing is in table
        self.notes_viewer.setPlaceholderText("Notes for this test case will appear here...")
        self.notes_viewer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.notes_viewer)


    @pyqtSlot(int, TestCase, int) # Slot receives same signal as stopwatch
    def update_test_case_info(self, row_index: int, test_case: TestCase, first_empty_iteration: int):
        """Updates the viewer with details of the selected test case."""
        self.current_test_case = test_case

        if test_case and test_case.name: # Check if it's a valid TC object
            self.name_label.setText(test_case.name)
            self.baseline_label.setText(f"Baseline: {test_case.baseline_ms if test_case.baseline_ms is not None else '--'} ms")
            self.priority_label.setText(f"Priority: {test_case.priority}")
            # Display Quip URL as a clickable link if available
            if test_case.quip_url:
                 self.quip_label.setText(f'Quip URL: <a href="{test_case.quip_url}">{test_case.quip_url}</a>')
            else:
                 self.quip_label.setText("Quip URL: --")


            self.steps_list.clear()
            if test_case.steps:
                for i, step in enumerate(test_case.steps):
                    self.steps_list.addItem(f"{i+1}. {step}")
            else:
                 self.steps_list.addItem("No steps defined.")

            self.notes_viewer.setText(test_case.test_notes)

        else: # No test case selected or invalid data
            self.name_label.setText("Select a Test Case")
            self.baseline_label.setText("Baseline: --")
            self.priority_label.setText("Priority: --")
            self.quip_label.setText("Quip URL: --")
            self.steps_list.clear()
            self.steps_list.addItem("Select a test case from the table to view steps.")
            self.notes_viewer.clear()


# Example Usage
if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication, QMainWindow
    import sys
    from ..utils.data_model import TestCase # Assuming ..utils exists

    app = QApplication(sys.argv)

    class MainWindowMock(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Test Steps Viewer")
            self.viewer = TestStepsViewerWidget()
            self.setCentralWidget(self.viewer)

            # Simulate receiving a test case update
            dummy_tc = TestCase(
                name="Sample Test Case",
                steps=["Step 1: Do this", "Step 2: Do that", "Step 3: Check result"],
                baseline_ms=1200.0,
                priority="P0",
                test_notes="These are some notes for the sample test case.",
                quip_url="https://example.com/quip/doc123"
            )
            # Use a QTimer to simulate signal emission after window shows
            QTimer.singleShot(100, lambda: self.viewer.update_test_case_info(0, dummy_tc, 0))

            # Simulate clearing selection after a delay
            QTimer.singleShot(3000, lambda: self.viewer.update_test_case_info(-1, TestCase(name=""), 0))


    main_window = MainWindowMock()
    main_window.show()
    sys.exit(app.exec_())