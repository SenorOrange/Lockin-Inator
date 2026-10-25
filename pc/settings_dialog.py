"""
Settings Dialog for Lockin-Inator PC.
Allows customizing study duration, break duration, and blocked desktop processes.
"""
from PyQt6 import QtCore, QtWidgets


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("Lockin-Inator Settings")
        self.setFixedSize(440, 480)
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                color: #f8fafc;
            }
            QLabel {
                color: #e2e8f0;
                font-size: 13px;
            }
            QSpinBox, QLineEdit {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px;
            }
            QListWidget {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px;
            }
            QCheckBox {
                color: #cbd5e1;
                font-size: 13px;
            }
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton#btnCancel {
                background-color: #334155;
            }
            QPushButton#btnCancel:hover {
                background-color: #475569;
            }
        """)

        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Heading
        title = QtWidgets.QLabel("⚙️ Focus & Timer Preferences")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #38bdf8;")
        layout.addWidget(title)

        # Durations
        dur_group = QtWidgets.QHBoxLayout()
        vbox_study = QtWidgets.QVBoxLayout()
        vbox_study.addWidget(QtWidgets.QLabel("Study Duration (min):"))
        self.spin_study = QtWidgets.QSpinBox()
        self.spin_study.setRange(5, 180)
        vbox_study.addWidget(self.spin_study)
        dur_group.addLayout(vbox_study)

        vbox_break = QtWidgets.QVBoxLayout()
        vbox_break.addWidget(QtWidgets.QLabel("AI Review Window (min):"))
        self.spin_break = QtWidgets.QSpinBox()
        self.spin_break.setRange(2, 60)
        vbox_break.addWidget(self.spin_break)
        dur_group.addLayout(vbox_break)
        layout.addLayout(dur_group)

        # Blocked Processes
        layout.addWidget(QtWidgets.QLabel("Blocked Desktop Applications:"))
        self.proc_list = QtWidgets.QListWidget()
        layout.addWidget(self.proc_list)

        add_layout = QtWidgets.QHBoxLayout()
        self.edit_proc = QtWidgets.QLineEdit()
        self.edit_proc.setPlaceholderText("e.g. godot.exe")
        add_layout.addWidget(self.edit_proc)

        btn_add = QtWidgets.QPushButton("+ Add")
        btn_add.clicked.connect(self._add_process)
        add_layout.addWidget(btn_add)

        btn_remove = QtWidgets.QPushButton("Remove")
        btn_remove.setObjectName("btnCancel")
        btn_remove.clicked.connect(self._remove_process)
        add_layout.addWidget(btn_remove)
        layout.addLayout(add_layout)

        # Toggles
        self.chk_sound = QtWidgets.QCheckBox("Play sound chimes on phase change")
        layout.addWidget(self.chk_sound)

        self.chk_cycle = QtWidgets.QCheckBox("Auto-cycle between study and review intervals")
        layout.addWidget(self.chk_cycle)

        layout.addStretch()

        # Dialog Buttons
        btn_box = QtWidgets.QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QtWidgets.QPushButton("Cancel")
        btn_cancel.setObjectName("btnCancel")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_save = QtWidgets.QPushButton("Save Changes")
        btn_save.clicked.connect(self._save_values)
        btn_box.addWidget(btn_save)

        layout.addLayout(btn_box)

    def _load_values(self):
        self.spin_study.setValue(self.config_manager.get("study_duration_minutes", 50))
        self.spin_break.setValue(self.config_manager.get("break_duration_minutes", 10))
        self.chk_sound.setChecked(self.config_manager.get("sound_enabled", True))
        self.chk_cycle.setChecked(self.config_manager.get("auto_cycle", True))

        self.proc_list.clear()
        for p in self.config_manager.get("blocked_processes", []):
            self.proc_list.addItem(p)

    def _add_process(self):
        text = self.edit_proc.text().strip().lower()
        if text:
            if not text.endswith(".exe"):
                text += ".exe"
            existing = [self.proc_list.item(i).text() for i in range(self.proc_list.count())]
            if text not in existing:
                self.proc_list.addItem(text)
            self.edit_proc.clear()

    def _remove_process(self):
        row = self.proc_list.currentRow()
        if row >= 0:
            self.proc_list.takeItem(row)

    def _save_values(self):
        self.config_manager.set("study_duration_minutes", self.spin_study.value())
        self.config_manager.set("break_duration_minutes", self.spin_break.value())
        self.config_manager.set("sound_enabled", self.chk_sound.isChecked())
        self.config_manager.set("auto_cycle", self.chk_cycle.isChecked())

        processes = [self.proc_list.item(i).text() for i in range(self.proc_list.count())]
        self.config_manager.set("blocked_processes", processes)
        self.accept()
