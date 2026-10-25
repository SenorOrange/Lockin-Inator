"""
Floating Break Pill for Lockin-Inator PC.
Maintained for backwards-compatibility; wraps FloatingTimerWidget.
"""
from .floating_timer import FloatingTimerWidget


class BreakPill(FloatingTimerWidget):
    def show_pill(self, remaining_seconds: int):
        self.show_widget("BREAK", remaining_seconds)
