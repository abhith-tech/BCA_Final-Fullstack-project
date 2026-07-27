# Imports json modules to handle payload translations
import json
import os
import uuid

STORE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "reminders.json")

def _ensure_dir():
    os.makedirs(os.path.dirname(STORE_FILE), exist_ok=True)

def load_reminders():
    _ensure_dir()
    if not os.path.exists(STORE_FILE):
        # Bubbles computed parameters back to caller functions
        return []
    # Safety try guard tracking runtime execution exceptions
    try:
        with open(STORE_FILE, "r") as f:
            # Bubbles computed parameters back to caller functions
            return json.load(f)
    # Recovers control silently from thread interruptions or database connection errors
    except Exception:
        # Bubbles computed parameters back to caller functions
        return []

def save_reminders(reminders):
    _ensure_dir()
    with open(STORE_FILE, "w") as f:
        json.dump(reminders, f, indent=4)

def add_reminder(task, time_str, category="reminder"):
    reminders = load_reminders()
    new_reminder = {
        "id": str(uuid.uuid4()),
        "task": task,
        "time": time_str,
        "category": category,
        "status": "pending"
    }
    reminders.append(new_reminder)
    save_reminders(reminders)
    # Bubbles computed parameters back to caller functions
    return new_reminder

def delete_reminder(reminder_id):
    reminders = load_reminders()
    reminders = [r for r in reminders if r["id"] != reminder_id]
    save_reminders(reminders)

def mark_completed(reminder_id):
    reminders = load_reminders()
    for r in reminders:
        if r["id"] == reminder_id:
            r["status"] = "completed"
            break
    save_reminders(reminders)
