"""
Floating Timer Widget for Lockin-Inator PC.
A sleek, draggable, always-on-top pill widget displayed on-screen during
Study and Break sessions, keeping the live timer visible without being distracting.
"""
from pathlib import Path
from PyQt6 import QtCore, QtGui, QtWidgets

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
LOGO_PATH = ASSETS_DIR / "lockin_logo.png"


class FloatingTimerWidget(QtWidgets.QWidget):
    lock_in_early_signal = QtCore.pyqtSignal()
    open_dashboard_signal = QtCore.pyqtSignal()
    end_session_signal = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = "IDLE"
        self._drag_pos = None
        self._is_moved_by_user = False
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
            | QtCore.Qt.WindowType.Tool
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedHeight(46)
        self.setFixedWidth(170)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)

        # Background frame (Pill)
        self.frame = QtWidgets.QFrame(self)
        self.frame.setObjectName("pillFrame")
        self._apply_study_style()

        frame_layout = QtWidgets.QHBoxLayout(self.frame)
        frame_layout.setContentsMargins(12, 4, 12, 4)
        frame_layout.setSpacing(8)
        frame_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # Icon / Status Emoji
        self.icon_label = QtWidgets.QLabel("🔒", self.frame)
        self.icon_label.setStyleSheet("font-size: 15px;")
        frame_layout.addWidget(self.icon_label)

        # Digital Countdown Label
        self.timer_label = QtWidgets.QLabel("50:00", self.frame)
        self.timer_label.setStyleSheet("""
            color: #38bdf8;
            font-size: 16px;
            font-weight: 800;
            font-family: Consolas, monospace;
            letter-spacing: 1px;
        """)
        frame_layout.addWidget(self.timer_label)

        # Break Action Button ("Lock In") - hidden during study
        self.btn_lock_in = QtWidgets.QPushButton("Lock In", self.frame)
        self.btn_lock_in.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_lock_in.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: #ffffff;
                border: none;
                border-radius: 10px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #047857;
            }
        """)
        self.btn_lock_in.setVisible(False)
        self.btn_lock_in.clicked.connect(self.lock_in_early_signal.emit)
        frame_layout.addWidget(self.btn_lock_in)

        layout.addWidget(self.frame)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.OpenHandCursor))

    def _apply_study_style(self):
        self.frame.setStyleSheet("""
            QFrame#pillFrame {
                background-color: rgba(15, 23, 42, 0.94);
                border: 2px solid #38bdf8;
                border-radius: 19px;
            }
        """)

    def _apply_break_style(self):
        self.frame.setStyleSheet("""
            QFrame#pillFrame {
                background-color: rgba(15, 23, 42, 0.94);
                border: 2px solid #10b981;
                border-radius: 19px;
            }
        """)

    def show_widget(self, state: str, remaining_seconds: int):
        self.state = state
        self.update_timer(remaining_seconds)

        if state == "STUDY":
            self._apply_study_style()
            self.icon_label.setText("🔒")
            self.timer_label.setStyleSheet("color: #38bdf8; font-size: 16px; font-weight: 800; font-family: Consolas, monospace; letter-spacing: 1px;")
            self.btn_lock_in.setVisible(False)
            self.setFixedWidth(170)
        elif state == "BREAK":
            self._apply_break_style()
            self.icon_label.setText("☕")
            self.timer_label.setStyleSheet("color: #10b981; font-size: 16px; font-weight: 800; font-family: Consolas, monospace; letter-spacing: 1px;")
            self.btn_lock_in.setVisible(True)
            self.setFixedWidth(240)

        if not self._is_moved_by_user:
            screen = QtGui.QGuiApplication.primaryScreen()
            if screen:
                geo = screen.geometry()
                self.move(geo.width() - self.width() - 30, 30)

        self.show()
        self.raise_()

    def update_timer(self, remaining_seconds: int):
        mins, secs = divmod(max(0, remaining_seconds), 60)
        self.timer_label.setText(f"{mins:02d}:{secs:02d}")

    # Dragging logic
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ClosedHandCursor))
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            self._is_moved_by_user = True
            event.accept()

    def mouseReleaseEvent(self, event):
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.OpenHandCursor))
        event.accept()

    # Double click opens dashboard
    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.open_dashboard_signal.emit()
            event.accept()

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 14px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #2563eb;
            }
        """)

        action_dash = menu.addAction("📱 Open Dashboard")
        action_dash.triggered.connect(self.open_dashboard_signal.emit)

        if self.state in ("STUDY", "BREAK"):
            menu.addSeparator()
            action_end = menu.addAction("🛑 End Study Session...")
            action_end.triggered.connect(self.end_session_signal.emit)

        menu.exec(event.globalPos())
