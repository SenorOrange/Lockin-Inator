"""
Friction Challenge Dialog for Lockin-Inator PC.
Prevents impulsive early breaks or session cancellations by requiring the user to type
a commitment phrase and wait through a cooldown timer before action can be confirmed.
"""
from PyQt6 import QtCore, QtGui, QtWidgets

COMMITMENT_PHRASE = "I am interrupting my study session early"
END_SESSION_PHRASE = "I want to end my study session now"


class FrictionChallengeDialog(QtWidgets.QDialog):
    def __init__(
        self,
        parent=None,
        delay_seconds=10,
        title="Stop & Think: Early Action Confirmation",
        target_phrase=COMMITMENT_PHRASE,
        button_text="Confirm Action",
        explanation=None
    ):
        super().__init__(parent)
        self.target_phrase = target_phrase
        self.remaining_seconds = delay_seconds
        self.custom_title = title
        self.custom_button_text = button_text
        self.custom_explanation = explanation

        self.setWindowTitle(f"Lockin-Inator - {title}")
        self.setFixedSize(500, 380)
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                color: #f8fafc;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QLabel {
                color: #e2e8f0;
            }
            QLineEdit {
                background-color: #1e293b;
                color: #f8fafc;
                border: 2px solid #334155;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }
            QLineEdit.match {
                border-color: #10b981;
                background-color: #064e3b;
            }
            QLineEdit.mismatch {
                border-color: #ef4444;
            }
            QPushButton#btnCancel {
                background-color: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 700;
            }
            QPushButton#btnCancel:hover {
                background-color: #1d4ed8;
            }
            QPushButton#btnUnlock {
                background-color: #334155;
                color: #64748b;
                border: 1px solid #475569;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton#btnUnlock:enabled {
                background-color: #dc2626;
                color: #ffffff;
                border-color: #ef4444;
            }
            QPushButton#btnUnlock:enabled:hover {
                background-color: #b91c1c;
            }
        """)

        self._setup_ui()

        # Cooldown timer
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start()

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # Warning Header
        header = QtWidgets.QHBoxLayout()
        icon = QtWidgets.QLabel("⚠️")
        icon.setStyleSheet("font-size: 28px;")
        header.addWidget(icon)

        title = QtWidgets.QLabel(self.custom_title)
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #f87171;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # Explanation
        default_exp = (
            "Study sessions are designed to keep you in flow until the timer finishes. "
            "To prevent impulsive actions, type the phrase below and wait for the cooldown."
        )
        desc_text = self.custom_explanation if self.custom_explanation else default_exp
        desc = QtWidgets.QLabel(desc_text)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94a3b8; font-size: 13px; line-height: 1.4;")
        layout.addWidget(desc)

        # Phrase Display
        phrase_box = QtWidgets.QFrame()
        phrase_box.setStyleSheet("background-color: #1e293b; border: 1px dashed #475569; border-radius: 8px; padding: 10px;")
        phrase_layout = QtWidgets.QVBoxLayout(phrase_box)
        phrase_layout.setContentsMargins(8, 8, 8, 8)

        phrase_lbl = QtWidgets.QLabel(f'"{self.target_phrase}"')
        phrase_lbl.setStyleSheet("color: #facc15; font-size: 14px; font-weight: 700; font-family: Consolas, monospace;")
        phrase_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        phrase_layout.addWidget(phrase_lbl)
        layout.addWidget(phrase_box)

        # Input Field
        self.input_edit = QtWidgets.QLineEdit()
        self.input_edit.setPlaceholderText("Type the exact phrase above...")
        self.input_edit.textChanged.connect(self._check_validation)
        layout.addWidget(self.input_edit)

        # Cooldown & Status Label
        if self.remaining_seconds > 0:
            self.status_lbl = QtWidgets.QLabel(f"⏳ Cooldown: {self.remaining_seconds}s remaining...")
        else:
            self.status_lbl = QtWidgets.QLabel("✅ Cooldown complete.")
        self.status_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600;")
        layout.addWidget(self.status_lbl)

        layout.addStretch()

        # Action Buttons
        btn_box = QtWidgets.QHBoxLayout()
        btn_box.setSpacing(12)

        # Default action encourages staying locked in
        self.btn_cancel = QtWidgets.QPushButton("Keep Studying (Cancel)")
        self.btn_cancel.setObjectName("btnCancel")
        self.btn_cancel.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        initial_btn_text = f"{self.custom_button_text} ({self.remaining_seconds}s)" if self.remaining_seconds > 0 else self.custom_button_text
        self.btn_unlock = QtWidgets.QPushButton(initial_btn_text)
        self.btn_unlock.setObjectName("btnUnlock")
        self.btn_unlock.setEnabled(False)
        self.btn_unlock.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_unlock.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_unlock)

        layout.addLayout(btn_box)

    def _on_tick(self):
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.status_lbl.setText(f"⏳ Cooldown: {self.remaining_seconds}s remaining...")
            if not self.btn_unlock.isEnabled():
                self.btn_unlock.setText(f"{self.custom_button_text} ({self.remaining_seconds}s)")
        else:
            self.timer.stop()
            self.status_lbl.setText("✅ Cooldown complete.")
            self._check_validation()

    def _check_validation(self):
        text = self.input_edit.text().strip()
        phrase_matched = (text == self.target_phrase)
        time_elapsed = (self.remaining_seconds <= 0)

        if phrase_matched:
            self.input_edit.setStyleSheet("border: 2px solid #10b981; background-color: #064e3b; color: #ffffff; padding: 10px; border-radius: 8px; font-size: 14px;")
        else:
            self.input_edit.setStyleSheet("border: 2px solid #334155; background-color: #1e293b; color: #ffffff; padding: 10px; border-radius: 8px; font-size: 14px;")

        if phrase_matched and time_elapsed:
            self.btn_unlock.setEnabled(True)
            self.btn_unlock.setText(self.custom_button_text)
        else:
            self.btn_unlock.setEnabled(False)
            if self.remaining_seconds > 0:
                self.btn_unlock.setText(f"{self.custom_button_text} ({self.remaining_seconds}s)")
            else:
                self.btn_unlock.setText("Type phrase to unlock")
