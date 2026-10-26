"""
System Tray Application and Core Controller for Lockin-Inator PC.
Manages the Pomodoro study/break state machine, process monitoring loop,
system tray notifications, and overlay coordination.
"""
import sys
from pathlib import Path
from PyQt6 import QtCore, QtGui, QtWidgets
import winsound

from .config import ConfigManager
from .process_monitor import ProcessMonitor
from .shield_overlay import MultiScreenShield
from .break_pill import BreakPill
from .floating_timer import FloatingTimerWidget
from .settings_dialog import SettingsDialog
from .dashboard_window import DashboardWindow
from .friction_dialog import FrictionChallengeDialog
from .sync_server import SyncManager

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
LOGO_PATH = ASSETS_DIR / "lockin_logo.png"

STATE_IDLE = "IDLE"
STATE_STUDY = "STUDY"
STATE_BREAK = "BREAK"
STATE_PAUSED = "PAUSED"


class LockinInatorPC(QtCore.QObject):
    remote_action_signal = QtCore.pyqtSignal(str, object)

    def __init__(self, app: QtWidgets.QApplication):
        super().__init__()
        self.app = app
        self.remote_action_signal.connect(self._execute_remote_action)
        self.config_manager = ConfigManager()
        self.process_monitor = ProcessMonitor(self.config_manager.get("blocked_processes"))

        self.state = STATE_IDLE
        self.prev_state = STATE_IDLE
        self.remaining_seconds = 0
        self.current_blocked_hwnd = None

        # UI Components
        self.shield_overlay = MultiScreenShield()
        self.shield_overlay.back_to_study_signal.connect(self._handle_back_to_study)
        self.shield_overlay.emergency_unlock_signal.connect(self._handle_emergency_unlock)
        self.shield_overlay.end_session_signal.connect(self.reset_session)

        # On-screen floating timer widget (compact, draggable pill)
        self.floating_widget = FloatingTimerWidget()
        self.floating_widget.lock_in_early_signal.connect(self.start_study_session)
        self.floating_widget.open_dashboard_signal.connect(self.show_dashboard)
        self.floating_widget.end_session_signal.connect(self._prompt_end_session)
        self.break_pill = self.floating_widget  # backwards compatibility

        # Local Wi-Fi Sync Hub (Syncs PC, Edge Extension, and Android Phone)
        self.sync_manager = SyncManager(port=8765)
        self.sync_manager.set_status_provider(self._get_sync_status)
        self.sync_manager.set_action_callback(self._handle_remote_action)
        self.sync_manager.start()

        # Dashboard Window
        self.dashboard = DashboardWindow(self.config_manager)
        self.dashboard.start_study_signal.connect(self.start_study_session)
        self.dashboard.start_break_signal.connect(self.start_break_session)
        self.dashboard.pause_signal.connect(self.pause_session)
        self.dashboard.resume_signal.connect(self.resume_session)
        self.dashboard.reset_signal.connect(self.reset_session)
        self.dashboard.open_settings_signal.connect(self._open_settings)
        self.dashboard.open_guide_signal.connect(self._show_autopilot_guide)

        # Timers
        self.clock_timer = QtCore.QTimer(self)
        self.clock_timer.setInterval(1000)
        self.clock_timer.timeout.connect(self._on_clock_tick)

        self.monitor_timer = QtCore.QTimer(self)
        self.monitor_timer.setInterval(250)
        self.monitor_timer.timeout.connect(self._check_foreground_process)

        # System Tray
        self._setup_tray()

    def _setup_tray(self):
        self.tray = QtWidgets.QSystemTrayIcon(self)
        if LOGO_PATH.exists():
            icon = QtGui.QIcon(str(LOGO_PATH))
        else:
            # Fallback icon
            pixmap = QtGui.QPixmap(32, 32)
            pixmap.fill(QtGui.QColor("#2563eb"))
            icon = QtGui.QIcon(pixmap)

        self.tray.setIcon(icon)
        self.tray.setToolTip("Lockin-Inator PC - Focus Assistant")
        self.tray.activated.connect(self._on_tray_activated)

        self.menu = QtWidgets.QMenu()
        self._rebuild_tray_menu()
        self.tray.setContextMenu(self.menu)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason in (
            QtWidgets.QSystemTrayIcon.ActivationReason.Trigger,
            QtWidgets.QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_dashboard()

    def show_dashboard(self):
        self.dashboard.show()
        self.dashboard.raise_()
        self.dashboard.activateWindow()

    def _rebuild_tray_menu(self):
        self.menu.clear()

        # Open Dashboard action
        action_dash = self.menu.addAction("📱 Open Lockin-Inator Dashboard")
        action_dash.triggered.connect(self.show_dashboard)
        self.menu.addSeparator()

        # Status item (disabled)
        if self.state == STATE_STUDY:
            mins, secs = divmod(self.remaining_seconds, 60)
            status_text = f"🔒 Studying: {mins:02d}:{secs:02d} left"
        elif self.state == STATE_BREAK:
            mins, secs = divmod(self.remaining_seconds, 60)
            status_text = f"☕ AI Review: {mins:02d}:{secs:02d} left"
        elif self.state == STATE_PAUSED:
            status_text = "⏸ Paused"
        else:
            status_text = "💤 Idle - Ready to Study"

        status_action = self.menu.addAction(status_text)
        status_action.setEnabled(False)
        self.menu.addSeparator()

        # Session controls
        if self.state != STATE_STUDY:
            study_min = self.config_manager.get("study_duration_minutes", 50)
            action_study = self.menu.addAction(f"▶ Start Study Session ({study_min}m)")
            action_study.triggered.connect(lambda: self.start_study_session())

        if self.state not in (STATE_STUDY, STATE_BREAK):
            break_min = self.config_manager.get("break_duration_minutes", 10)
            action_break = self.menu.addAction(f"☕ Start AI Review Window ({break_min}m)")
            action_break.triggered.connect(lambda: self.start_break_session())

        if self.state == STATE_STUDY:
            action_break_early = self.menu.addAction("☕ Request Early Break (Challenge)...")
            action_break_early.triggered.connect(self._prompt_early_break)

            action_end_study = self.menu.addAction("🛑 End Study Session (Challenge)...")
            action_end_study.triggered.connect(self._prompt_end_session)

        if self.state == STATE_BREAK:
            action_lock_early = self.menu.addAction("🔒 Lock In Early (Start Study)")
            action_lock_early.triggered.connect(lambda: self.start_study_session())

            action_end_break = self.menu.addAction("🛑 Return to Idle (End Session)")
            action_end_break.triggered.connect(self.reset_session)

        if self.state == STATE_PAUSED:
            action_resume = self.menu.addAction("▶ Resume Timer")
            action_resume.triggered.connect(self.resume_session)

        self.menu.addSeparator()

        # Settings
        action_settings = self.menu.addAction("⚙️ Settings...")
        action_settings.triggered.connect(self._open_settings)

        # Autopilot Guide
        action_guide = self.menu.addAction("📖 Autopilot Prompt Guide...")
        action_guide.triggered.connect(self._show_autopilot_guide)

        # Widget Physics Mode Toggle
        action_physics = self.menu.addAction("⚽ Widget Physics Mode (Bouncing & 1.5x)")
        action_physics.setCheckable(True)
        action_physics.setChecked(self.floating_widget.physics_enabled)
        action_physics.toggled.connect(self.floating_widget.set_physics_enabled)

        self.menu.addSeparator()

        # Quit
        action_quit = self.menu.addAction("❌ Exit Lockin-Inator")
        action_quit.triggered.connect(self._quit)

    def start_study_session(self, duration_minutes=None):
        if duration_minutes is None:
            duration_minutes = self.config_manager.get("study_duration_minutes", 50)
        self.state = STATE_STUDY
        self.remaining_seconds = duration_minutes * 60
        self.floating_widget.show_widget(self.state, self.remaining_seconds)

        self.clock_timer.start()
        self.monitor_timer.start()

        self._play_sound(winsound.MB_ICONASTERISK)
        self._notify("🔒 Locked In!", f"Study mode started for {duration_minutes} minutes. Claude & Antigravity will keep working in the background.")
        self.dashboard.update_state(self.state, self.remaining_seconds)
        self.sync_manager.broadcast_update()
        self._rebuild_tray_menu()

    def start_break_session(self, duration_minutes=None):
        if duration_minutes is None:
            duration_minutes = self.config_manager.get("break_duration_minutes", 10)
        self.state = STATE_BREAK
        self.remaining_seconds = duration_minutes * 60

        self.monitor_timer.stop()
        self.shield_overlay.hide_shield()
        self.floating_widget.show_widget(self.state, self.remaining_seconds)

        self.clock_timer.start()

        self._play_sound(winsound.MB_OK)
        self._notify("☕ Break & AI Review Time!", f"You have {duration_minutes} minutes to check Claude/Antigravity and queue your next game dev prompts.")
        self.dashboard.update_state(self.state, self.remaining_seconds)
        self.sync_manager.broadcast_update()
        self._rebuild_tray_menu()

    def pause_session(self):
        if self.state in (STATE_STUDY, STATE_BREAK):
            self.prev_state = self.state
            self.state = STATE_PAUSED
            self.clock_timer.stop()
            self.monitor_timer.stop()
            self.shield_overlay.hide_shield()
            self.floating_widget.hide()
            self._notify("⏸ Paused", "Timer paused. Lockin-Inator focus shield is temporarily disarmed.")
            self.dashboard.update_state(self.state, self.remaining_seconds)
            self.sync_manager.broadcast_update()
            self._rebuild_tray_menu()

    def resume_session(self):
        if self.state == STATE_PAUSED:
            self.state = self.prev_state
            self.clock_timer.start()
            if self.state == STATE_STUDY:
                self.monitor_timer.start()
            self.floating_widget.show_widget(self.state, self.remaining_seconds)
            self._notify("▶ Resumed", "Timer resumed.")
            self.dashboard.update_state(self.state, self.remaining_seconds)
            self.sync_manager.broadcast_update()
            self._rebuild_tray_menu()

    def reset_session(self):
        self.state = STATE_IDLE
        self.clock_timer.stop()
        self.monitor_timer.stop()
        self.shield_overlay.hide_shield()
        self.floating_widget.hide()
        self.remaining_seconds = self.config_manager.get("study_duration_minutes", 50) * 60
        self.dashboard.update_state(self.state, self.remaining_seconds)
        self.sync_manager.broadcast_update()
        self._rebuild_tray_menu()

    def _on_clock_tick(self):
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1

            # Update active overlays
            if self.state == STATE_STUDY:
                mins, secs = divmod(self.remaining_seconds, 60)
                self.tray.setToolTip(f"Lockin-Inator: Studying ({mins:02d}:{secs:02d} left)")
                if self.shield_overlay.isVisible():
                    self.shield_overlay.update_timer(self.remaining_seconds)

            elif self.state == STATE_BREAK:
                mins, secs = divmod(self.remaining_seconds, 60)
                self.tray.setToolTip(f"Lockin-Inator: AI Review ({mins:02d}:{secs:02d} left)")

            if self.floating_widget.isVisible():
                self.floating_widget.update_timer(self.remaining_seconds)

            if self.dashboard.isVisible():
                self.dashboard.update_state(self.state, self.remaining_seconds)

            # Broadcast update periodically to keep clients in sync
            self.sync_manager.broadcast_update()
        else:
            # Timer reached zero!
            if self.state == STATE_STUDY:
                if self.config_manager.get("auto_cycle", True):
                    self.start_break_session()
                else:
                    self.state = STATE_IDLE
                    self.clock_timer.stop()
                    self.monitor_timer.stop()
                    self.shield_overlay.hide_shield()
                    self.floating_widget.hide()
                    self._play_sound(winsound.MB_OK)
                    self._notify("🎉 Session Complete", "Study session completed! Great job.")
                    self._rebuild_tray_menu()

            elif self.state == STATE_BREAK:
                if self.config_manager.get("auto_cycle", True):
                    self.start_study_session()
                else:
                    self.state = STATE_IDLE
                    self.clock_timer.stop()
                    self.floating_widget.hide()
                    self._play_sound(winsound.MB_ICONEXCLAMATION)
                    self._notify("⏰ Break Over", "Break time is up. Ready to lock back in?")
                    self._rebuild_tray_menu()

    def _check_foreground_process(self):
        if self.state != STATE_STUDY:
            return

        if self.process_monitor.is_in_cooldown():
            return

        hwnd, pid, pname, title = self.process_monitor.get_foreground_info()
        if not pname:
            return

        # Do not block our own overlay, floating widget, or dashboard
        if (
            hwnd in self.shield_overlay.get_window_ids()
            or hwnd == int(self.floating_widget.winId())
            or hwnd == int(self.dashboard.winId())
        ):
            return

        if self.process_monitor.is_blocked(pname):
            self.current_blocked_hwnd = hwnd
            if not self.shield_overlay.isVisible():
                self.shield_overlay.show_shield(hwnd, pname, self.remaining_seconds)

    def _handle_back_to_study(self):
        self.process_monitor.trigger_cooldown(1.5)
        self.shield_overlay.hide_shield()
        if self.current_blocked_hwnd:
            self.process_monitor.minimize_window(self.current_blocked_hwnd)
            self.current_blocked_hwnd = None

    def _handle_emergency_unlock(self):
        self._notify("🔓 Early Review Window", "Early unlock challenge passed. You have a 10-minute review window.")
        self.start_break_session(duration_minutes=self.config_manager.get("break_duration_minutes", 10))

    def _prompt_end_session(self):
        if self.state == STATE_BREAK:
            self.reset_session()
            return

        dlg = FrictionChallengeDialog(
            None,
            delay_seconds=10,
            title="End Study Session Early",
            target_phrase="I want to end my study session now",
            button_text="End Session & Unlock",
            explanation="Ending your study session early will disarm the focus shields and return Lockin-Inator to Idle. Type the phrase below to confirm."
        )
        if dlg.exec():
            self.reset_session()

    def _prompt_early_break(self):
        dlg = FrictionChallengeDialog(
            None,
            delay_seconds=10,
            title="Request Early Break",
            target_phrase="I am interrupting my study session early",
            button_text="Unlock AI Review",
            explanation="This will transition you into a 10-minute AI Review break window."
        )
        if dlg.exec():
            self.start_break_session(duration_minutes=self.config_manager.get("break_duration_minutes", 10))

    def _play_sound(self, sound_type):
        if self.config_manager.get("sound_enabled", True):
            try:
                winsound.MessageBeep(sound_type)
            except Exception:
                pass

    def _notify(self, title, message):
        if self.config_manager.get("notifications_enabled", True):
            self.tray.showMessage(title, message, QtWidgets.QSystemTrayIcon.MessageIcon.Information, 4000)

    def _open_settings(self):
        dlg = SettingsDialog(self.config_manager)
        if dlg.exec():
            self.process_monitor.update_blocked_processes(self.config_manager.get("blocked_processes"))
            self.sync_manager.broadcast_update()
            self._rebuild_tray_menu()

    def _show_autopilot_guide(self):
        guide = QtWidgets.QMessageBox()
        guide.setWindowTitle("Lockin-Inator Autopilot Prompt Guide")
        guide.setTextFormat(QtCore.Qt.TextFormat.RichText)
        guide.setText("""
            <h3>🚀 How to Keep Prompts Flowing While Studying</h3>
            <p>Don't prompt line-by-line every 10 minutes. Use <b>Milestone Autopilot</b>:</p>
            <ol>
                <li><b>Use /goal in Antigravity:</b> Type <code>/goal</code> before starting a game-dev sprint. Antigravity will work through the full feature autonomously without stopping.</li>
                <li><b>In Claude Desktop:</b> Give multi-step milestone instructions:
                    <br><i>"Build Milestone 2: 1) implement physics, 2) create asset loader, 3) write test suite. Complete all steps and run tests before stopping."</i>
                </li>
                <li><b>Lock In for 50 minutes:</b> Let the models generate and build in the background while you study.</li>
                <li><b>Review during the 10-minute break:</b> Test the game, review changes, queue the next milestone, and lock back in!</li>
            </ol>
        """)
        guide.exec()

    def _get_sync_status(self) -> dict:
        return {
            "state": self.state,
            "remaining_seconds": self.remaining_seconds,
            "study_duration_minutes": self.config_manager.get("study_duration_minutes", 50),
            "break_duration_minutes": self.config_manager.get("break_duration_minutes", 10),
            "blocked_sites": self.config_manager.get("blocked_sites", [
                "instagram.com", "youtube.com", "tiktok.com", "twitter.com",
                "x.com", "reddit.com", "twitch.tv", "facebook.com", "netflix.com"
            ]),
        }

    def _handle_remote_action(self, action: str, duration: Optional[int]) -> bool:
        if action in ("START_STUDY", "LOCK_IN", "START_BREAK", "RESET"):
            self.remote_action_signal.emit(action, duration)
            return True
        return False

    def _execute_remote_action(self, action: str, duration: Optional[int]):
        if action in ("START_STUDY", "LOCK_IN"):
            self.start_study_session(duration)
        elif action == "START_BREAK":
            self.start_break_session(duration)
        elif action == "RESET":
            self.reset_session()

    def _quit(self):
        self.sync_manager.stop()
        self.clock_timer.stop()
        self.monitor_timer.stop()
        self.shield_overlay.hide_shield()
        self.floating_widget.close()
        self.dashboard.close()
        self.tray.hide()
        self.app.quit()
