"""
Multi-Screen Focus Shield Overlay for Lockin-Inator PC.
Blocks ALL connected monitors simultaneously whenever a blocked application
is focused during a study session, while allowing background tasks to continue.
"""
from pathlib import Path
from PyQt6 import QtCore, QtGui, QtWidgets
from .friction_dialog import FrictionChallengeDialog

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
LOGO_PATH = ASSETS_DIR / "lockin_logo.png"


class SingleScreenShield(QtWidgets.QWidget):
    back_to_study_signal = QtCore.pyqtSignal()
    emergency_unlock_signal = QtCore.pyqtSignal()

    def __init__(self, screen, is_interactive=True, parent=None):
        super().__init__(parent)
        self.target_screen = screen
        self.is_interactive = is_interactive
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
            | QtCore.Qt.WindowType.Tool
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setGeometry(self.target_screen.geometry())

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # Card container
        self.card = QtWidgets.QFrame(self)
        self.card.setObjectName("shieldCard")
        self.card.setFixedSize(540, 500 if self.is_interactive else 380)
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
            self.logo_label.setPixmap(pixmap.scaled(64, 64, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
        card_layout.addWidget(self.logo_label)

        # Title
        title_text = "🔒 Focus Mode Active" if self.is_interactive else "🔒 All Screens Locked"
        self.title_label = QtWidgets.QLabel(title_text, self.card)
        self.title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("color: #f8fafc; font-size: 24px; font-weight: 700; font-family: 'Segoe UI', sans-serif;")
        card_layout.addWidget(self.title_label)

        # Badge
        self.badge_label = QtWidgets.QLabel("Shielded: Claude & Antigravity", self.card)
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

        # Digital Countdown
        self.timer_label = QtWidgets.QLabel("00:00", self.card)
        self.timer_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setStyleSheet("""
            color: #38bdf8;
            font-size: 46px;
            font-weight: 800;
            font-family: Consolas, monospace;
            letter-spacing: 2px;
        """)
        card_layout.addWidget(self.timer_label)

        # Explanation
        self.subtext_label = QtWidgets.QLabel(
            "Claude & Antigravity are cooking in the background!\nFocus on studying. Prompts unlock when the timer hits zero.",
            self.card
        )
        self.subtext_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.subtext_label.setWordWrap(True)
        self.subtext_label.setStyleSheet("color: #94a3b8; font-size: 13px; line-height: 1.4;")
        card_layout.addWidget(self.subtext_label)

        if self.is_interactive:
            card_layout.addSpacing(6)

            # Primary action: Back to Studying
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

            # High-friction emergency unlock challenge
            self.btn_emergency = QtWidgets.QPushButton("⚠️ Early Unlock Challenge...", self.card)
            self.btn_emergency.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            self.btn_emergency.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #64748b;
                    border: none;
                    font-size: 12px;
                    padding: 4px;
                }
                QPushButton:hover {
                    color: #f87171;
                }
            """)
            self.btn_emergency.clicked.connect(self._open_friction_challenge)
            card_layout.addWidget(self.btn_emergency)

        main_layout.addWidget(self.card)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        try:
            painter.fillRect(self.rect(), QtGui.QColor(15, 23, 42, 235))
        finally:
            painter.end()

    def update_timer(self, remaining_seconds: int):
        mins, secs = divmod(max(0, remaining_seconds), 60)
        self.timer_label.setText(f"{mins:02d}:{secs:02d}")

    def _on_back_clicked(self):
        # Post via timer queue so Qt finishes handling the click event cleanly
        QtCore.QTimer.singleShot(0, self.back_to_study_signal.emit)

    def _open_friction_challenge(self):
        dlg = FrictionChallengeDialog(self, delay_seconds=15)
        if dlg.exec():
            QtCore.QTimer.singleShot(50, self.emergency_unlock_signal.emit)


class MultiScreenShield(QtCore.QObject):
    """
    Coordinates simultaneous full-screen focus shields across all connected monitors.
    Maintains persistent window instances to avoid Qt allocation churn and crashes.
    """
    back_to_study_signal = QtCore.pyqtSignal()
    emergency_unlock_signal = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.windows = []
        self.blocked_hwnd = None
        self.blocked_app_name = ""
        self.remaining_seconds = 0
        self._is_visible = False
        self._init_windows()

    def _init_windows(self):
        for w in self.windows:
            w.hide()
            w.deleteLater()
        self.windows.clear()

        screens = QtGui.QGuiApplication.screens()
        primary_screen = QtGui.QGuiApplication.primaryScreen()

        for s in screens:
            is_primary = (s == primary_screen)
            w = SingleScreenShield(s, is_interactive=is_primary)
            if is_primary:
                w.back_to_study_signal.connect(self.back_to_study_signal.emit)
                w.emergency_unlock_signal.connect(self.emergency_unlock_signal.emit)
            self.windows.append(w)

    def isVisible(self):
        return self._is_visible

    def show_shield(self, blocked_hwnd: int, app_name: str, remaining_seconds: int):
        self.blocked_hwnd = blocked_hwnd
        self.blocked_app_name = app_name
        self.remaining_seconds = remaining_seconds

        # Ensure windows match current screen count
        screens = QtGui.QGuiApplication.screens()
        if len(screens) != len(self.windows):
            self._init_windows()

        primary_screen = QtGui.QGuiApplication.primaryScreen()
        clean_name = app_name.replace(".exe", "").capitalize()

        for w in self.windows:
            w.update_timer(remaining_seconds)
            if w.is_interactive:
                w.badge_label.setText(f"Locked App: {clean_name}")
            w.show()
            w.raise_()
            if w.target_screen == primary_screen:
                w.activateWindow()

        self._is_visible = True

    def update_timer(self, remaining_seconds: int):
        self.remaining_seconds = remaining_seconds
        for w in self.windows:
            w.update_timer(remaining_seconds)

    def hide_shield(self):
        for w in self.windows:
            w.hide()
        self._is_visible = False

    def hide(self):
        self.hide_shield()

    def get_window_ids(self):
        return [int(w.winId()) for w in self.windows]
