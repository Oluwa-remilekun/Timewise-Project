"""Exceptions raised by the domain layer and shown to the user by the UI."""


class ValidationError(ValueError):
    """User input failed a domain rule; the message is safe to display."""
