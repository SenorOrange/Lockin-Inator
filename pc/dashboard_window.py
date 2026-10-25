"""
Main Dashboard Window for Lockin-Inator PC.
Provides an interactive command center to start/stop focus sessions,
adjust timer presets, view shielded apps, and access settings.
"""
from pathlib import Path
from PyQt6 import QtCore, QtGui, QtWidgets
from .friction_dialog import FrictionChallengeDialog

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
LOGO_PATH = ASSETS_DIR / "lockin_logo.png"


class DashboardWindow(QtWidgets.QWidget):
    start_study_signal = QtCore.pyqtSignal(int)
    start_break_signal = QtCore.pyqtSignal(int)
    pause_signal = QtCore.pyqtSignal()
    resume_signal = QtCore.pyqtSignal()
    reset_signal = QtCore.pyqtSignal()
    open_settings_signal = QtCore.pyqtSignal()
    open_guide_signal = QtCore.pyqtSignal()

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.selected_duration = self.config_manager.get("study_duration_minutes", 50)
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Lockin-Inator PC Focus Assistant")
        self.setFixedSize(480, 600)
        self.setStyleSheet("""
            QWidget {
                background-color: #0b1120;
                color: #f8fafc;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QFrame#card {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 16px;
            }
            QLabel#title {
                font-size: 22px;
                font-weight: 800;
                color: #f8fafc;
            }
            QLabel#subtitle {
                font-size: 13px;
                color: #94a3b8;
            }
            QLabel#timer {
                font-size: 52px;
                font-weight: 800;
                font-family: Consolas, monospace;
                color: #38bdf8;
                letter-spacing: 2px;
            }
            QPushButton.chip {
                background-color: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton.chip:hover {
                color: #f8fafc;
                background-color: #334155;
            }
            QPushButton.chip.active {
                background-color: #2563eb;
                color: #ffffff;
                border-color: #3b82f6;
            }
            QPushButton#btnMain {
                background-color: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 12px;
                padding: 14px;
                font-size: 16px;
                font-weight: 700;
            }
            QPushButton#btnMain:hover {
                background-color: #1d4ed8;
            }
            QPushButton#btnMain:pressed {
                background-color: #1e40af;
            }
            QPushButton.secondary {
                background-color: #1e293b;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 10px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton.secondary:hover {
                background-color: #334155;
                color: #f8fafc;
            }
        """)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header = QtWidgets.QHBoxLayout()
        header.setSpacing(14)
        if LOGO_PATH.exists():
            logo = QtWidgets.QLabel()
            pixmap = QtGui.QPixmap(str(LOGO_PATH)).scaled(48, 48, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
            logo.setPixmap(pixmap)
            header.addWidget(logo)

        header_vbox = QtWidgets.QVBoxLayout()
        title_lbl = QtWidgets.QLabel("Lockin-Inator PC")
        title_lbl.setObjectName("title")
        header_vbox.addWidget(title_lbl)

        sub_lbl = QtWidgets.QLabel("Focus Shield & Pomodoro Assistant")
        sub_lbl.setObjectName("subtitle")
        header_vbox.addWidget(sub_lbl)
        header.addLayout(header_vbox)
        header.addStretch()

        btn_settings_top = QtWidgets.QPushButton("⚙️")
        btn_settings_top.setFixedSize(36, 36)
        btn_settings_top.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        btn_settings_top.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; font-size: 16px;")
        btn_settings_top.clicked.connect(self.open_settings_signal.emit)
        header.addWidget(btn_settings_top)

        layout.addLayout(header)

        # Main Timer Card
        self.card = QtWidgets.QFrame()
        self.card.setObjectName("card")
        card_layout = QtWidgets.QVBoxLayout(self.card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)
        card_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # Status badge
        self.badge_status = QtWidgets.QLabel("💤 IDLE - READY TO STUDY")
        self.badge_status.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.badge_status.setStyleSheet("""
            color: #38bdf8;
            background-color: #032b43;
            border: 1px solid #0369a1;
            border-radius: 12px;
            padding: 4px 14px;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 1px;
        """)
        card_layout.addWidget(self.badge_status)

        # Digital Clock
        mins = self.selected_duration
        self.timer_label = QtWidgets.QLabel(f"{mins:02d}:00")
        self.timer_label.setObjectName("timer")
        self.timer_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.timer_label)

        # Preset Chips
        self.chip_layout = QtWidgets.QHBoxLayout()
        self.chip_layout.setSpacing(10)
        self.chips = {}
        for d in [25, 45, 50, 60]:
            btn = QtWidgets.QPushButton(f"{d} min")
            btn.setProperty("class", "chip")
            btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            if d == self.selected_duration:
                btn.setStyleSheet("background-color: #2563eb; color: #ffffff; border: 1px solid #3b82f6; border-radius: 8px; padding: 6px 14px; font-weight: 600;")
            else:
                btn.setStyleSheet("background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; border-radius: 8px; padding: 6px 14px; font-weight: 600;")
            btn.clicked.connect(lambda checked, dur=d: self._select_preset(dur))
            self.chips[d] = btn
            self.chip_layout.addWidget(btn)
        card_layout.addLayout(self.chip_layout)

        # Action Button
        self.btn_main = QtWidgets.QPushButton("🔒 START STUDY SESSION")
        self.btn_main.setObjectName("btnMain")
        self.btn_main.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_main.clicked.connect(self._on_main_action_clicked)
        card_layout.addWidget(self.btn_main)

        # High-friction early break link (only shown during study mode)
        self.btn_force_break = QtWidgets.QPushButton("⚠️ Request Early Break (Challenge Required)...")
        self.btn_force_break.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_force_break.setStyleSheet("""
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
        self.btn_force_break.setVisible(False)
        self.btn_force_break.clicked.connect(self._on_force_break_clicked)
        card_layout.addWidget(self.btn_force_break)

        # Sub-controls (Hidden during active lock-in to prevent bypass loopholes)
        self.sub_controls = QtWidgets.QHBoxLayout()
        self.sub_controls.setSpacing(10)

        self.btn_pause = QtWidgets.QPushButton("⏸ Pause")
        self.btn_pause.setProperty("class", "secondary")
        self.btn_pause.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_pause.clicked.connect(self._toggle_pause)
        self.btn_pause.setVisible(False)
        self.sub_controls.addWidget(self.btn_pause)

        self.btn_reset = QtWidgets.QPushButton("⏹ Reset")
        self.btn_reset.setProperty("class", "secondary")
        self.btn_reset.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_reset.clicked.connect(self.reset_signal.emit)
        self.btn_reset.setVisible(False)
        self.sub_controls.addWidget(self.btn_reset)

        card_layout.addLayout(self.sub_controls)
        layout.addWidget(self.card)

        # Shielded Apps Info Card
        apps_card = QtWidgets.QFrame()
        apps_card.setObjectName("card")
        apps_layout = QtWidgets.QVBoxLayout(apps_card)
        apps_layout.setContentsMargins(16, 14, 16, 14)
        apps_layout.setSpacing(6)

        apps_title = QtWidgets.QLabel("🛡️ Shielded Desktop Applications:")
        apps_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #e2e8f0;")
        apps_layout.addWidget(apps_title)

        self.apps_label = QtWidgets.QLabel("• Claude Desktop  • Antigravity IDE  • VS Code")
        self.apps_label.setStyleSheet("font-size: 13px; color: #38bdf8;")
        apps_layout.addWidget(self.apps_label)

        sub_info = QtWidgets.QLabel("Background agents continue running, but their windows are shielded to keep you focused on studying.")
        sub_info.setWordWrap(True)
        sub_info.setStyleSheet("font-size: 12px; color: #64748b; line-height: 1.3;")
        apps_layout.addWidget(sub_info)

        layout.addWidget(apps_card)

        # Bottom Bar
        bottom = QtWidgets.QHBoxLayout()
        btn_guide = QtWidgets.QPushButton("📖 Autopilot Guide")
        btn_guide.setProperty("class", "secondary")
        btn_guide.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        btn_guide.setStyleSheet("background-color: transparent; color: #94a3b8; border: none; font-size: 12px;")
        btn_guide.clicked.connect(self.open_guide_signal.emit)
        bottom.addWidget(btn_guide)
        bottom.addStretch()

        btn_hide = QtWidgets.QPushButton("Minimize to Tray")
        btn_hide.setProperty("class", "secondary")
        btn_hide.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        btn_hide.setStyleSheet("background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; border-radius: 6px; padding: 6px 12px; font-size: 12px;")
        btn_hide.clicked.connect(self.hide)
        bottom.addWidget(btn_hide)

        layout.addLayout(bottom)

    def _select_preset(self, minutes):
        self.selected_duration = minutes
        mins, secs = minutes, 0
        self.timer_label.setText(f"{mins:02d}:{secs:02d}")
        for d, btn in self.chips.items():
            if d == minutes:
                btn.setStyleSheet("background-color: #2563eb; color: #ffffff; border: 1px solid #3b82f6; border-radius: 8px; padding: 6px 14px; font-weight: 600;")
            else:
                btn.setStyleSheet("background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; border-radius: 8px; padding: 6px 14px; font-weight: 600;")

    def _on_main_action_clicked(self):
        btn_text = self.btn_main.text()
        if "START STUDY" in btn_text:
            self.start_study_signal.emit(self.selected_duration)
        elif "LOCK IN NOW" in btn_text:
            self.start_study_signal.emit(self.selected_duration)

    def _on_force_break_clicked(self):
        dlg = FrictionChallengeDialog(self, delay_seconds=15)
        if dlg.exec():
            self.start_break_signal.emit(self.config_manager.get("break_duration_minutes", 10))

    def _toggle_pause(self):
        if self.btn_pause.text() == "⏸ Pause":
            self.pause_signal.emit()
        else:
            self.resume_signal.emit()

    def update_state(self, state: str, remaining_seconds: int):
        mins, secs = divmod(max(0, remaining_seconds), 60)
        self.timer_label.setText(f"{mins:02d}:{secs:02d}")

        if state == "STUDY":
            self.badge_status.setText("🔒 STUDY MODE ACTIVE")
            self.badge_status.setStyleSheet("color: #38bdf8; background-color: #032b43; border: 1px solid #0369a1; border-radius: 12px; padding: 4px 14px; font-size: 12px; font-weight: 700;")
            self.btn_main.setText("🔒 STUDY IN PROGRESS (LOCKED)")
            self.btn_main.setEnabled(False)
            self.btn_main.setStyleSheet("background-color: #1e293b; color: #64748b; border: 1px solid #334155; border-radius: 12px; padding: 14px; font-size: 15px; font-weight: 700;")
            self.btn_force_break.setVisible(True)
            self.btn_pause.setVisible(False)
            self.btn_reset.setVisible(False)

        elif state == "BREAK":
            self.badge_status.setText("☕ AI REVIEW WINDOW OPEN")
            self.badge_status.setStyleSheet("color: #34d399; background-color: #064e3b; border: 1px solid #059669; border-radius: 12px; padding: 4px 14px; font-size: 12px; font-weight: 700;")
            self.btn_main.setText("🔒 LOCK IN NOW (END BREAK EARLY)")
            self.btn_main.setEnabled(True)
            self.btn_main.setStyleSheet("background-color: #2563eb; color: #ffffff; border: none; border-radius: 12px; padding: 14px; font-size: 16px; font-weight: 700;")
            self.btn_force_break.setVisible(False)
            self.btn_pause.setVisible(False)
            self.btn_reset.setVisible(False)

        elif state == "PAUSED":
            self.badge_status.setText("⏸ PAUSED")
            self.badge_status.setStyleSheet("color: #fbbf24; background-color: #451a03; border: 1px solid #b45309; border-radius: 12px; padding: 4px 14px; font-size: 12px; font-weight: 700;")
            self.btn_pause.setText("▶ Resume")

        else:  # IDLE
            self.badge_status.setText("💤 IDLE - READY TO STUDY")
            self.badge_status.setStyleSheet("color: #38bdf8; background-color: #032b43; border: 1px solid #0369a1; border-radius: 12px; padding: 4px 14px; font-size: 12px; font-weight: 700;")
            self.btn_main.setText("🔒 START STUDY SESSION")
            self.btn_main.setEnabled(True)
            self.btn_main.setStyleSheet("background-color: #2563eb; color: #ffffff; border: none; border-radius: 12px; padding: 14px; font-size: 16px; font-weight: 700;")
            self.btn_force_break.setVisible(False)
            self.btn_pause.setVisible(False)
            self.btn_reset.setVisible(False)
            mins = self.selected_duration
            self.timer_label.setText(f"{mins:02d}:00")

    def closeEvent(self, event):
        # Instead of quitting, hide to tray so blocker keeps running
        event.ignore()
        self.hide()
