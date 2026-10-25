"""
Unit tests for Lockin-Inator PC Focus Assistant.
"""
import sys
from pathlib import Path
import pytest
from PyQt6 import QtWidgets

# Ensure pc package is importable
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pc.config import ConfigManager, DEFAULT_CONFIG
from pc.process_monitor import ProcessMonitor
from pc.shield_overlay import ShieldOverlay
from pc.break_pill import BreakPill
from pc.dashboard_window import DashboardWindow
from pc.tray_app import LockinInatorPC, STATE_IDLE, STATE_STUDY, STATE_BREAK, STATE_PAUSED


@pytest.fixture(scope="session")
def qapp():
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication([])
    return app


def test_config_manager(tmp_path):
    cfg_file = tmp_path / "test_config.json"
    mgr = ConfigManager(config_path=cfg_file)

    # Defaults
    assert mgr.get("study_duration_minutes") == 50
    assert mgr.get("break_duration_minutes") == 10
    assert "claude.exe" in mgr.get("blocked_processes")
    assert "antigravity.exe" in mgr.get("blocked_processes")

    # Mutation & Save
    mgr.set("study_duration_minutes", 45)
    assert mgr.get("study_duration_minutes") == 45

    # Reload from file
    mgr2 = ConfigManager(config_path=cfg_file)
    assert mgr2.get("study_duration_minutes") == 45


def test_process_monitor():
    monitor = ProcessMonitor(["claude.exe", "antigravity.exe", "code.exe"])

    assert monitor.is_blocked("claude.exe")
    assert monitor.is_blocked("Claude.exe")
    assert monitor.is_blocked("Antigravity.exe")
    assert monitor.is_blocked("Code.exe")
    assert not monitor.is_blocked("notepad.exe")
    assert not monitor.is_blocked("chrome.exe")
    assert not monitor.is_blocked(None)

    # Dynamic update
    monitor.update_blocked_processes(["godot.exe"])
    assert monitor.is_blocked("godot.exe")
    assert not monitor.is_blocked("claude.exe")


def test_shield_overlay_timer(qapp):
    overlay = ShieldOverlay()
    overlay.update_timer(125)  # 2m 5s
    assert overlay.timer_label.text() == "02:05"

    overlay.update_timer(0)
    assert overlay.timer_label.text() == "00:00"


def test_break_pill_timer(qapp):
    pill = BreakPill()
    pill.update_timer(600)  # 10m
    assert pill.timer_label.text() == "AI Review: 10:00"

    pill.update_timer(59)  # 59s
    assert pill.timer_label.text() == "AI Review: 00:59"


def test_dashboard_window(qapp, tmp_path):
    cfg_file = tmp_path / "test_dash_config.json"
    mgr = ConfigManager(config_path=cfg_file)
    dash = DashboardWindow(mgr)

    # Preset selection
    dash._select_preset(25)
    assert dash.selected_duration == 25
    assert dash.timer_label.text() == "25:00"

    # State update
    dash.update_state("STUDY", 25 * 60)
    assert "STUDY MODE ACTIVE" in dash.badge_status.text()

    dash.update_state("BREAK", 10 * 60)
    assert "AI REVIEW WINDOW" in dash.badge_status.text()

    dash.update_state("IDLE", 50 * 60)
    assert "IDLE" in dash.badge_status.text()


def test_state_transitions(qapp, tmp_path):
    cfg_file = tmp_path / "test_state_config.json"
    controller = LockinInatorPC(qapp)
    controller.config_manager = ConfigManager(config_path=cfg_file)

    assert controller.state == STATE_IDLE

    # Start study
    controller.start_study_session(duration_minutes=50)
    assert controller.state == STATE_STUDY
    assert controller.remaining_seconds == 50 * 60
    assert controller.clock_timer.isActive()

    # Pause
    controller.pause_session()
    assert controller.state == STATE_PAUSED
    assert not controller.clock_timer.isActive()

    # Resume
    controller.resume_session()
    assert controller.state == STATE_STUDY
    assert controller.clock_timer.isActive()

    # Switch to break
    controller.start_break_session(duration_minutes=10)
    assert controller.state == STATE_BREAK
    assert controller.remaining_seconds == 10 * 60
    assert controller.break_pill.isVisible()

    # Clean up
    controller.clock_timer.stop()
    controller.monitor_timer.stop()
    controller.break_pill.hide()
    controller.shield_overlay.hide()
    controller.tray.hide()
