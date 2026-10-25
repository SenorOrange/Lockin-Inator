"""
Focus Shield Overlay for Lockin-Inator PC.
Displays a distraction-blocking screen whenever a blocked application
is focused during a study session, while allowing background tasks to continue.
"""
import os
from pathlib import Path
from PyQt6 import QtCore, QtGui, QtWidgets

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
LOGO_PATH = ASSETS_DIR / "lockin_logo.png"


class ShieldOverlay(QtWidgets.QWidget):
    back_to_study_signal = QtCore.pyqtSignal()
    emergency_unlock_signal = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.blocked_hwnd = None
        self.blocked_app_name = ""
        self.remaining_seconds = 0
        self.emergency_countdown = 10
        self.emergency_timer = QtCore.QTimer(self)
        self.emergency_timer.setInterval(1000)
        self.emergency_timer.timeout.connect(self._tick_emergency)

        self._setup_ui()

    def _setup_ui(self):
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
            | QtCore.Qt.WindowType.Tool
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Full screen layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # Card container
        self.card = QtWidgets.QFrame(self)
        self.card.setObjectName("shieldCard")
        self.card.setFixedSize(540, 520)
        self.card.setStyleSheet("""
            QFrame#shieldCard {
                background-color: #0f172a;
                border: 2px solid #334155;
                border-radius: 20px;
            }
        """)

        card_layout = QtWidgets.QVBoxLayout(self.card)
        card_layout.setContentsMargins(36, 32, 36, 32)
        card_layout.setSpacing(14)
        card_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # App Logo
        self.logo_label = QtWidgets.QLabel(self.card)
        self.logo_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        if LOGO_PATH.exists():
            pixmap = QtGui.QPixmap(str(LOGO_PATH))
            self.logo_label.setPixmap(pixmap.scaled(72, 72, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
        card_layout.addWidget(self.logo_label)

        # Title
        self.title_label = QtWidgets.QLabel("🔒 Focus Mode Active", self.card)
        self.title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("color: #f8fafc; font-size: 24px; font-weight: 700; font-family: Segoe UI, sans-serif;")
        card_layout.addWidget(self.title_label)

        # Blocked app badge
        self.badge_label = QtWidgets.QLabel("Blocked: AI Game Dev Tool", self.card)
        self.badge_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.badge_label.setStyleSheet("""
            color: #f59e0b;
            background-color: #451a03;
            border: 1px solid #78350f;
            border-radius: 12px;
            padding: 4px 14px;
            font-size: 13px;
            font-weight: 600;
        """)
        card_layout.addWidget(self.badge_label)

        # Countdown Timer Display
        self.timer_label = QtWidgets.QLabel("00:00", self.card)
        self.timer_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setStyleSheet("""
            color: #38bdf8;
            font-size: 48px;
            font-weight: 800;
            font-family: Consolas, monospace;
            letter-spacing: 2px;
        """)
        card_layout.addWidget(self.timer_label)

        # Subtext explaining agents are working in background
        self.subtext_label = QtWidgets.QLabel(
            "Claude & Antigravity are cooking in the background!\nReview & prompt window opens when the timer hits zero.",
            self.card
        )
        self.subtext_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.subtext_label.setWordWrap(True)
        self.subtext_label.setStyleSheet("color: #94a3b8; font-size: 14px; line-height: 1.4;")
        card_layout.addWidget(self.subtext_label)

        card_layout.addSpacing(10)

        # Action Buttons
        self.btn_back = QtWidgets.QPushButton("Back to Studying", self.card)
        self.btn_back.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 10px;
                padding: 12px 24px;
                font-size: 15px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:pressed {
                background-color: #1e40af;
            }
        """)
        self.btn_back.clicked.connect(self._on_back_clicked)
        card_layout.addWidget(self.btn_back)

        self.btn_emergency = QtWidgets.QPushButton("Emergency Unlock (10s hold)", self.card)
        self.btn_emergency.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_emergency.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #64748b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                color: #ef4444;
                border-color: #ef4444;
            }
        """)
        self.btn_emergency.clicked.connect(self._on_emergency_clicked)
        card_layout.addWidget(self.btn_emergency)

        main_layout.addWidget(self.card)

    def paintEvent(self, event):
        # Draw translucent dark overlay behind card
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor(15, 23, 42, 220))

    def show_shield(self, blocked_hwnd: int, app_name: str, remaining_seconds: int):
        self.blocked_hwnd = blocked_hwnd
        self.blocked_app_name = app_name
        self.remaining_seconds = remaining_seconds

        # Update labels
        clean_name = app_name.replace(".exe", "").capitalize()
        self.badge_label.setText(f"Locked App: {clean_name}")
        self.update_timer(remaining_seconds)

        # Resize to full primary screen
        screen = QtGui.QGuiApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

        self.show()
        self.raise_()
        self.activateWindow()

    def update_timer(self, remaining_seconds: int):
        self.remaining_seconds = remaining_seconds
        mins, secs = divmod(max(0, remaining_seconds), 60)
        self.timer_label.setText(f"{mins:02d}:{secs:02d}")

    def _on_back_clicked(self):
        self.hide()
        self.back_to_study_signal.emit()

    def _on_emergency_clicked(self):
        if not self.emergency_timer.isActive():
            self.emergency_countdown = 10
            self.btn_emergency.setText(f"Unlocking in {self.emergency_countdown}s... Click to Cancel")
            self.emergency_timer.start()
        else:
            self.emergency_timer.stop()
            self.btn_emergency.setText("Emergency Unlock (10s hold)")

    def _tick_emergency(self):
        self.emergency_countdown -= 1
        if self.emergency_countdown <= 0:
            self.emergency_timer.stop()
            self.btn_emergency.setText("Emergency Unlock (10s hold)")
            self.hide()
            self.emergency_unlock_signal.emit()
        else:
            self.btn_emergency.setText(f"Unlocking in {self.emergency_countdown}s... Click to Cancel")
