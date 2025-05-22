# utils/file_manager.py
import json
import os
from typing import Optional, List, Dict, Any
from .data_model import Session, TestCase
import csv # For basic CSV export
# import openpyxl # Optional: For Excel export
# import pandas as pd # Optional: For easier Excel/CSV handling

# --- Configuration ---
# Get user's home directory and create a hidden directory for app data
APP_DATA_DIR = os.path.join(os.path.expanduser("~"), ".kindleperfmate")
SESSIONS_DIR = os.path.join(APP_DATA_DIR, "sessions")
TEMPLATES_DIR = os.path.join(APP_DATA_DIR, "templates")

# Ensure directories exist
os.makedirs(SESSIONS_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# --- Session Management ---
def save_session(session: Session, filename: Optional[str] = None) -> str:
    """Saves the current session to a JSON file."""
    if filename is None:
        # Generate a default filename based on session info
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_week = session.week.replace(" ", "_").replace("/", "-")
        safe_device = session.device.replace(" ", "_").replace("/", "-")
        filename = f"session_{safe_week}_{safe_device}_{timestamp}.json"

    filepath = os.path.join(SESSIONS_DIR, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(session.to_dict(), f, indent=2)

    print(f"Session saved to {filepath}")
    return filepath # Return the path where it was saved

def load_session(filepath: str) -> Optional[Session]:
    """Loads a session from a JSON file."""
    if not os.path.exists(filepath):
        print(f"Error: File not found at {filepath}")
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return Session.from_dict(data)
    except Exception as e:
        print(f"Error loading session from {filepath}: {e}")
        return None

def list_sessions() -> List[Dict[str, Any]]:
    """Lists available session files with basic info (requires loading each partially or relying on filename)."""
    sessions_list = []
    for filename in os.listdir(SESSIONS_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(SESSIONS_DIR, filename)
            try:
                # Load partial data to get session info without parsing all test cases
                with open(filepath, 'r', encoding='utf-8') as f:
                    # Read only the beginning to get week, device, build, start_time
                    # This is a simplified approach; full load is safer but slower for many files.
                    # A better approach for large history is a separate index file or SQLite.
                    # For now, let's do a full load as sessions aren't expected to be huge initially.
                    session_data = json.load(f)
                    sessions_list.append({
                        "filename": filename,
                        "filepath": filepath,
                        "week": session_data.get("week", "N/A"),
                        "device": session_data.get("device", "N/A"),
                        "build": session_data.get("build", "N/A"),
                        "start_time": session_data.get("start_time", "N/A"),
                        "test_case_count": len(session_data.get("test_cases", []))
                    })
            except Exception as e:
                print(f"Warning: Could not read info from {filename}: {e}")
                sessions_list.append({
                    "filename": filename,
                    "filepath": filepath,
                    "week": "Error", "device": "Error", "build": "Error", "start_time": "Error", "test_case_count": 0
                })
    # Sort by time, newest first (requires parsing date strings)
    sessions_list.sort(key=lambda x: x.get("start_time", ""), reverse=True)
    return sessions_list


# --- Test Case Templates ---
def load_test_case_template(priority: str) -> List[TestCase]:
    """Loads test case definitions from a template file based on priority."""
    # Define a simple template file naming convention
    template_file = os.path.join(TEMPLATES_DIR, f"test_cases_{priority.lower()}.json")

    if not os.path.exists(template_file):
        print(f"Warning: Template file not found for priority '{priority}' at {template_file}.")
        print("Loading sample data or returning empty list.")
        # --- Create a sample template if not found ---
        if priority == "P0":
             sample_data = [
                 TestCase(name="App Launch", steps=["Tap app icon", "Wait for main screen"], priority="P0", baseline_ms=1000),
                 TestCase(name="Cold Boot to Home", steps=["Reboot device", "Time until home screen appears"], priority="P0", baseline_ms=45000),
                 TestCase(name="Open Settings", steps=["Tap 'Settings'", "Wait for settings page"], priority="P0", baseline_ms=800)
             ]
        elif priority == "P1":
             sample_data = [
                 TestCase(name="Open Library", steps=["Tap 'Library'", "Wait for library list"], priority="P1", baseline_ms=1500),
                 TestCase(name="Open Store", steps=["Tap 'Store'", "Wait for store home page"], priority="P1", baseline_ms=2000)
             ]
        else:
            sample_data = []

        # Save sample data as a template file for next time
        try:
            os.makedirs(TEMPLATES_DIR, exist_ok=True)
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump([tc.to_dict() for tc in sample_data], f, indent=2)
            print(f"Created sample template: {template_file}")
            return sample_data # Return the sample data we just created
        except Exception as e:
             print(f"Error creating sample template: {e}")
             return [] # Return empty if cannot create sample


    try:
        with open(template_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Assuming the JSON is a list of TestCase dictionaries
            return [TestCase.from_dict(tc_data) for tc_data in data]
    except Exception as e:
        print(f"Error loading template from {template_file}: {e}")
        return []

# --- Exporting Data ---
def export_session_to_csv(session: Session, filepath: str):
    """Exports session data to a CSV file."""
    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)

            # Write header row
            header = ["Test Case", "Priority"]
            for i in range(1, 6):
                header.append(f"Iteration {i} (ms)")
                header.append(f"Iteration {i} Notes")
                header.append(f"Iteration {i} Skipped")
            header.extend(["Average (ms)", "Baseline (ms)", "Test Case Notes", "Steps", "Quip URL"])
            writer.writerow(header)

            # Write data rows
            for tc in session.test_cases:
                row = [tc.name, tc.priority]
                for i in range(5):
                    iter_data = tc.iterations[i] if i < len(tc.iterations) else Iteration()
                    row.append(iter_data.time_ms if iter_data.time_ms is not None else "")
                    row.append(iter_data.notes)
                    row.append("Yes" if iter_data.skipped else "No")

                average_ms = calculate_average(tc.iterations) # Need timer_utils here
                row.append(average_ms if average_ms is not None else "")
                row.append(tc.baseline_ms if tc.baseline_ms is not None else "")
                row.append(tc.test_notes)
                row.append("; ".join(tc.steps)) # Join steps into a single string
                row.append(tc.quip_url)

                writer.writerow(row)
        print(f"Data exported successfully to {filepath}")
    except Exception as e:
        print(f"Error exporting to CSV: {e}")

# Example Usage (for testing file manager)
if __name__ == '__main__':
    # Need a dummy calculate_average for this standalone test
    def calculate_average(iterations):
         valid_times = [iter.time_ms for iter in iterations if iter.time_ms is not None and not iter.skipped]
         return sum(valid_times) / len(valid_times) if valid_times else None

    # Test loading templates
    p0_template = load_test_case_template("P0")
    print(f"\nLoaded {len(p0_template)} P0 test cases from template.")
    if p0_template:
        print(f"First P0 case: {p0_template[0].name}")

    p1_template = load_test_case_template("P1")
    print(f"Loaded {len(p1_template)} P1 test cases from template.")
     if p1_template:
        print(f"First P1 case: {p1_template[0].name}")


    # Test saving/loading a session
    test_session = Session(week="Wk43", device="PW4", build="14.6.0.1", priority_filter="P0")
    test_session.test_cases = p0_template # Use the loaded template as session data

    # Add some dummy data to iterations
    if test_session.test_cases:
        test_session.test_cases[0].iterations[0] = Iteration(time_ms=1050, notes="Warm start")
        test_session.test_cases[0].iterations[1] = Iteration(time_ms=980)
        test_session.test_cases[1].iterations[0] = Iteration(time_ms=46000, skipped=True, notes="Device hung")


    saved_path = save_session(test_session)
    loaded_session = load_session(saved_path)

    if loaded_session:
        print(f"\nLoaded session: Week={loaded_session.week}, Device={loaded_session.device}, Build={loaded_session.build}")
        print(f"Test cases loaded: {len(loaded_session.test_cases)}")
        if loaded_session.test_cases:
             print(f"First TC iterations: {[iter.time_ms for iter in loaded_session.test_cases[0].iterations]}")


    # Test listing sessions
    print("\nAvailable sessions:")
    session_files = list_sessions()
    for info in session_files:
        print(f"- {info['filename']} | Week: {info['week']}, Device: {info['device']}, TCs: {info['test_case_count']}")

    # Test export to CSV
    export_filepath = os.path.join(APP_DATA_DIR, "export_example.csv")
    export_session_to_csv(test_session, export_filepath)
    print(f"CSV Exported to: {export_filepath}")