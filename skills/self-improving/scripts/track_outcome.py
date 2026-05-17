#!/usr/bin/env python3
"""
Track task outcomes for self-improvement.
Called automatically after complex tasks or manually via 'learn from this'.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

STORAGE_DIR = Path.home() / ".hermes" / "self-improving"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def load_patterns():
    path = STORAGE_DIR / "error_patterns.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


def save_patterns(patterns):
    path = STORAGE_DIR / "error_patterns.json"
    with open(path, "w") as f:
        json.dump(patterns, f, indent=2)


def load_performance():
    path = STORAGE_DIR / "performance.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"tasks": {}, "total": 0, "successful": 0}


def save_performance(perf):
    path = STORAGE_DIR / "performance.json"
    with open(path, "w") as f:
        json.dump(perf, f, indent=2)


def track_outcome(task_type: str, success: bool, errors: list[str], tool_calls: int):
    """Track a task outcome."""
    perf = load_performance()
    
    if task_type not in perf["tasks"]:
        perf["tasks"][task_type] = {"total": 0, "successful": 0, "avg_tool_calls": 0}
    
    task_stats = perf["tasks"][task_type]
    task_stats["total"] += 1
    if success:
        task_stats["successful"] += 1
        perf["successful"] += 1
    
    # Update average tool calls
    n = task_stats["total"]
    task_stats["avg_tool_calls"] = (task_stats["avg_tool_calls"] * (n - 1) + tool_calls) / n
    
    perf["total"] += 1
    save_performance(perf)
    
    # Track error patterns
    if errors:
        patterns = load_patterns()
        for error in errors:
            # Simple pattern matching
            found = False
            for p in patterns:
                if p["pattern"] in error or error in p["pattern"]:
                    p["frequency"] += 1
                    p["last_seen"] = datetime.now().isoformat()
                    found = True
                    break
            if not found:
                patterns.append({
                    "pattern": error[:200],  # Truncate long errors
                    "context": task_type,
                    "frequency": 1,
                    "last_seen": datetime.now().isoformat(),
                })
        save_patterns(patterns)
    
    print(f"[Self-Improving] Tracked: {task_type} | Success: {success} | Tools: {tool_calls}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: track_outcome.py <task_type> <success|failure> <tool_calls> [errors...]")
        sys.exit(1)
    
    task_type = sys.argv[1]
    success = sys.argv[2].lower() == "success"
    tool_calls = int(sys.argv[3])
    errors = sys.argv[4:] if len(sys.argv) > 4 else []
    
    track_outcome(task_type, success, errors, tool_calls)
