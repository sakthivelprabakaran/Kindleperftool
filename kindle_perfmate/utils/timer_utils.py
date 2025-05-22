# utils/timer_utils.py
from typing import List, Optional
from .data_model import Iteration # Assuming they are in the same utils package

def format_time(milliseconds: Optional[float]) -> str:
    """Formats milliseconds into a human-readable string (e.g., "1.234s" or "0.500s")."""
    if milliseconds is None:
        return "--"
    seconds = milliseconds / 1000.0
    return f"{seconds:.3f}s"

def calculate_average(iterations: List[Iteration]) -> Optional[float]:
    """Calculates the average of valid iteration times."""
    valid_times = [iter.time_ms for iter in iterations if iter.time_ms is not None and not iter.skipped]
    if not valid_times:
        return None
    return sum(valid_times) / len(valid_times)

def calculate_spike(iteration_ms: Optional[float], baseline_ms: Optional[float], average_ms: Optional[float]) -> Optional[float]:
    """Calculates spike percentage relative to baseline or average."""
    if iteration_ms is None or iteration_ms <= 0:
        return None

    if baseline_ms is not None and baseline_ms > 0:
        # Compare to baseline if available
        return ((iteration_ms - baseline_ms) / baseline_ms) * 100
    elif average_ms is not None and average_ms > 0:
        # Otherwise compare to average (excluding the current iteration for fairness, but simple average is fine initially)
        # Note: A more accurate average for spike detection would exclude the current iteration.
        # For simplicity, we'll use the average *including* the current iteration for now.
         return ((iteration_ms - average_ms) / average_ms) * 100
    return None # No baseline or average to compare against

# Example Usage
if __name__ == '__main__':
    iters = [
        Iteration(time_ms=550),
        Iteration(time_ms=600),
        Iteration(time_ms=580),
        Iteration(time_ms=1200, notes="Spike?"),
        Iteration(time_ms=610)
    ]
    avg = calculate_average(iters)
    print(f"Average time: {format_time(avg)}") # Should be around 708ms if spike is included
    print(f"Formatted time: {format_time(1234.56)}")
    print(f"Formatted None: {format_time(None)}")

    baseline = 500.0
    spike1 = calculate_spike(iters[0].time_ms, baseline, avg)
    spike4 = calculate_spike(iters[3].time_ms, baseline, avg)
    print(f"Iteration 1 spike vs baseline ({format_time(baseline)}): {spike1:.2f}%" if spike1 is not None else "N/A")
    print(f"Iteration 4 spike vs baseline ({format_time(baseline)}): {spike4:.2f}%" if spike4 is not None else "N/A")

    no_baseline_avg = calculate_average([iters[0], iters[1], iters[2], iters[4]]) # Average excluding spike
    spike4_vs_avg = calculate_spike(iters[3].time_ms, None, no_baseline_avg)
    print(f"Iteration 4 spike vs avg ({format_time(no_baseline_avg)}): {spike4_vs_avg:.2f}%" if spike4_vs_avg is not None else "N/A")