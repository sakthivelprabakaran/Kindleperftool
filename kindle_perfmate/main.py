# main.py
import sys
import os
from PyQt5.QtWidgets import QApplication
from .main_window import MainWindow
from .utils.file_manager import APP_DATA_DIR # Import to ensure dir is created on first run

if __name__ == "__main__":
    # Ensure app data directory exists before launching
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    print(f"Application data directory: {APP_DATA_DIR}")

    app = QApplication(sys.argv)
    app.setApplicationName("KindlePerfMate")
    app.setOrganizationName("YourOrganization") # Optional: for settings management

    main_window = MainWindow()
    main_window.show()

    sys.exit(app.exec_())