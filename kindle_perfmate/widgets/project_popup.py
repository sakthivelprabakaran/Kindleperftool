# widgets/project_popup.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLabel,
                             QLineEdit, QDialogButtonBox, QComboBox)
from PyQt5.QtCore import Qt

class ProjectPopup(QDialog):
    """Dialog to capture new project/session details."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Performance Session")
        self.setModal(True)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.form_layout = QFormLayout()

        self.week_input = QLineEdit()
        self.device_input = QLineEdit()
        self.build_input = QLineEdit()
        self.priority_combo = QComboBox()
        # Add typical priorities and the 'All' option
        self.priority_combo.addItems(["All", "P0", "P1", "P2", "P3", "750"])

        self.form_layout.addRow("Week Number:", self.week_input)
        self.form_layout.addRow("Device Details:", self.device_input)
        self.form_layout.addRow("Build Number:", self.build_input)
        self.form_layout.addRow("Default Priority Filter:", self.priority_combo)

        self.layout.addLayout(self.form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.layout.addWidget(self.button_box)

        # Set some defaults (optional)
        # self.week_input.setText("WkXX")
        # self.device_input.setText("Kindle Paperwhite X")
        # self.build_input.setText("14.x.y.z")


    def get_data(self) -> dict:
        """Returns the data entered in the form."""
        return {
            "week": self.week_input.text().strip(),
            "device": self.device_input.text().strip(),
            "build": self.build_input.text().strip(),
            "priority_filter": self.priority_combo.currentText()
        }

# Example Usage (for testing the popup)
if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    dialog = ProjectPopup()
    if dialog.exec_() == QDialog.Accepted:
        project_data = dialog.get_data()
        print("New Project Data:")
        print(project_data)
    else:
        print("New Project Cancelled")
    sys.exit(app.exec_())