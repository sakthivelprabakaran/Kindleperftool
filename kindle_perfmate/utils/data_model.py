# utils/data_model.py
import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class Iteration:
    """Represents a single test iteration result."""
    time_ms: Optional[float] = None  # Time in milliseconds
    notes: str = ""
    skipped: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Iteration':
        return Iteration(**data)

@dataclass
class TestCase:
    """Represents a single performance test case."""
    name: str
    steps: List[str] = field(default_factory=list)
    baseline_ms: Optional[float] = None # Baseline time in milliseconds
    priority: str = "P3" # e.g., P0, P1, P2, P3, 750
    iterations: List[Iteration] = field(default_factory=lambda: [Iteration() for _ in range(5)]) # Fixed 5 iterations
    test_notes: str = "" # Notes specific to this test case
    quip_url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "steps": self.steps,
            "baseline_ms": self.baseline_ms,
            "priority": self.priority,
            "iterations": [iter.to_dict() for iter in self.iterations],
            "test_notes": self.test_notes,
            "quip_url": self.quip_url
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TestCase':
        data['iterations'] = [Iteration.from_dict(iter_data) for iter_data in data.get('iterations', [{} for _ in range(5)])]
        # Ensure exactly 5 iterations are created if fewer were saved or none exist
        while len(data['iterations']) < 5:
            data['iterations'].append(Iteration())
        data['iterations'] = data['iterations'][:5] # Trim if somehow more than 5 were saved
        return TestCase(**data)


@dataclass
class Session:
    """Represents a performance test session (project)."""
    week: str = ""
    device: str = ""
    build: str = ""
    priority_filter: str = "All" # The filter applied in the UI for this session
    test_cases: List[TestCase] = field(default_factory=list)
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: Optional[str] = None
    global_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "week": self.week,
            "device": self.device,
            "build": self.build,
            "priority_filter": self.priority_filter,
            "test_cases": [tc.to_dict() for tc in self.test_cases],
            "start_time": self.start_time,
            "end_time": self.end_time,
            "global_notes": self.global_notes
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Session':
        data['test_cases'] = [TestCase.from_dict(tc_data) for tc_data in data.get('test_cases', [])]
        return Session(**data)

# Example Usage (for testing data model)
if __name__ == '__main__':
    # Create a sample session
    session = Session(
        week="Wk42",
        device="Paperwhite 5",
        build="14.5.1.2",
        priority_filter="P0"
    )
    tc1 = TestCase(
        name="Open Book Home",
        steps=["Tap 'Home'", "Wait for rendering"],
        priority="P0",
        baseline_ms=500.0
    )
    tc1.iterations[0] = Iteration(time_ms=620.0, notes="Fast load")
    tc1.iterations[1] = Iteration(time_ms=580.0)

    tc2 = TestCase(
        name="Search for Term",
        steps=["Tap Search icon", "Type 'performance'", "Tap Search"],
        priority="P1",
        baseline_ms=1200.0
    )
    tc2.iterations[0] = Iteration(time_ms=1350.0)

    session.test_cases.append(tc1)
    session.test_cases.append(tc2)

    # Save to JSON (simulated)
    session_dict = session.to_dict()
    print("--- Session Dict ---")
    print(json.dumps(session_dict, indent=2))

    # Load from JSON (simulated)
    loaded_session_dict = json.loads(json.dumps(session_dict)) # Simulate saving/loading
    loaded_session = Session.from_dict(loaded_session_dict)

    print("\n--- Loaded Session ---")
    print(f"Week: {loaded_session.week}")
    print(f"Device: {loaded_session.device}")
    print(f"Test Cases: {len(loaded_session.test_cases)}")
    print(f"First Test Case: {loaded_session.test_cases[0].name}")
    print(f"First Iteration time: {loaded_session.test_cases[0].iterations[0].time_ms} ms")