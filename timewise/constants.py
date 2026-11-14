"""Domain constants shared by the data, analytics and UI layers."""

ACTIVITY_CATEGORIES = ("Productive", "Unproductive", "Fun")
ACTIVITY_CATEGORY_COLORS = {
    "Productive": "#12a594",
    "Unproductive": "#f9735b",
    "Fun": "#f5b83d",
}
ACTIVITY_CATEGORY_EMOJI = {
    "Productive": "🎯",
    "Unproductive": "🌀",
    "Fun": "🎉",
}
MAX_ACTIVITY_MINUTES = 24 * 60

TASK_CATEGORIES = ("School", "Work", "Life", "Urgent")
TASK_CATEGORY_COLORS = {
    "School": "blue",
    "Work": "green",
    "Life": "orange",
    "Urgent": "red",
}
TASK_CATEGORY_EMOJI = {
    "School": "📚",
    "Work": "💼",
    "Life": "🌿",
    "Urgent": "🚨",
}

REMINDER_SOURCE_TYPES = ("Event", "Task")
REPEAT_INTERVALS = {
    "Does not repeat": 0,
    "Hourly": 60,
    "Daily": 24 * 60,
    "Weekly": 7 * 24 * 60,
}

MAX_TITLE_LENGTH = 100
