import json
import os

LOG_FILE = "log.json"  # adjust if your log file has a different name

def load_log():
    """Load existing log; return empty list if file doesn't exist or is invalid."""
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, 'r') as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except json.JSONDecodeError:
        print(f"Warning: {LOG_FILE} is corrupted. Starting with empty log.")
        # Optionally backup the corrupted file
        if os.path.exists(LOG_FILE):
            os.rename(LOG_FILE, f"{LOG_FILE}.corrupted")
        return []
