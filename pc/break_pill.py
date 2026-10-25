"""
Floating Break Pill for Lockin-Inator PC.
A sleek, non-intrusive floating indicator displayed during the Break / AI Review window
so the user can track their prompt review time and lock back in when ready.
"""
from pathlib import Path
from PyQt6 import QtCore, QtGui, QtWidgets

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
LOGO_PATH = ASSETS_DIR / "lockin_logo.png"


class BreakPill(QtWidgets.QWidget):
    lock_in_early_signal = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._drag_pos = None

    def _setup_ui(self):
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
            | QtCore.Qt.WindowType.Tool
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedHeight(54)
        self.setFixedWidth(360)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 14, 6)
        layout.setSpacing(10)

        # Background frame
        self.frame = QtWidgets.QFrame(self)
        self.frame.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 23, 42, 0.95);
                border: 2px solid #10b981;
                border-radius: 20px;
            }
        """)
        frame_layout = QtWidgets.QHBoxLayout(self.frame)
        frame_layout.setContentsMargins(12, 4, 12, 4)
        frame_layout.setSpacing(10)

        # Icon/Emoji
        self.icon_label = QtWidgets.QLabel("☕", self.frame)
        self.icon_label.setStyleSheet("font-size: 18px;")
        frame_layout.addWidget(self.icon_label)

        # Status & Timer text
        self.timer_label = QtWidgets.QLabel("AI Review: 10:00", self.frame)
        self.timer_label.setStyleSheet("""
            color: #10b981;
            font-size: 14px;
            font-weight: 700;
            font-family: Consolas, monospace;
        """)
        frame_layout.addWidget(self.timer_label)

        frame_layout.addStretch()

        # "Lock In Early" button
        self.btn_lock_in = QtWidgets.QPushButton("Lock In", self.frame)
        self.btn_lock_in.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_lock_in.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: #ffffff;
                border: none;
                border-radius: 12px;
                padding: 4px 12px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #047857;
            }
        """)
        self.btn_lock_in.clicked.connect(self._on_lock_in_clicked)
        frame_layout.addWidget(self.btn_lock_in)

        layout.addWidget(self.frame)

    def show_pill(self, remaining_seconds: int):
        self.update_timer(remaining_seconds)
        # Position in top right corner of primary screen
        screen = QtGui.QGuiApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            self.move(geo.width() - self.width() - 40, 40)
        self.show()
        self.raise_()

    def update_timer(self, remaining_seconds: int):
        mins, secs = divmod(max(0, remaining_seconds), 60)
        self.timer_label.setText(f"AI Review: {mins:02d}:{secs:02d}")

    def _on_lock_in_clicked(self):
        self.hide()
        self.lock_in_early_signal.emit()

    # Enable dragging the pill
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
