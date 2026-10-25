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
from pc.shield_overlay import MultiScreenShield, SingleScreenShield
from pc.friction_dialog import FrictionChallengeDialog, COMMITMENT_PHRASE
from pc.break_pill import BreakPill
from pc.floating_timer import FloatingTimerWidget
from pc.dashboard_window import DashboardWindow
from pc.sync_server import SyncManager
from pc.settings_dialog import SettingsDialog
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
    overlay = MultiScreenShield()
    overlay.show_shield(1234, "claude.exe", 125)
    assert overlay.isVisible()
    assert len(overlay.windows) >= 1

    overlay.update_timer(125)
    primary_w = [w for w in overlay.windows if w.is_interactive][0]
    assert primary_w.timer_label.text() == "02:05"

    overlay.hide_shield()
    assert not overlay.isVisible()


def test_friction_dialog(qapp):
    dlg = FrictionChallengeDialog(delay_seconds=0)
    # Target phrase must match exactly
    assert dlg.target_phrase == COMMITMENT_PHRASE

    dlg.input_edit.setText("wrong phrase")
    dlg._check_validation()
    assert not dlg.btn_unlock.isEnabled()

    dlg.input_edit.setText(COMMITMENT_PHRASE)
    dlg._check_validation()
    assert dlg.btn_unlock.isEnabled()


def test_break_pill_timer(qapp):
    pill = BreakPill()
    pill.update_timer(600)  # 10m
    assert pill.timer_label.text() == "10:00"

    pill.update_timer(59)  # 59s
    assert pill.timer_label.text() == "00:59"


def test_floating_timer_widget(qapp):
    widget = FloatingTimerWidget()
    widget.show_widget("STUDY", 50 * 60)
    assert widget.icon_label.text() == "🔒"
    assert widget.timer_label.text() == "50:00"
    assert not widget.btn_lock_in.isVisible()

    widget.show_widget("BREAK", 10 * 60)
    assert widget.icon_label.text() == "☕"
    assert widget.timer_label.text() == "10:00"
    assert widget.btn_lock_in.isVisible()


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
    controller.sync_manager.stop()


def test_sync_server():
    import urllib.request
    import json
    import time

    mgr = SyncManager(port=8768)
    mgr.set_status_provider(lambda: {"state": "STUDY", "remaining_seconds": 1200})
    mgr.set_action_callback(lambda act, dur: True)
    mgr.start()
    time.sleep(0.3)

    try:
        # Status endpoint
        req = urllib.request.urlopen("http://127.0.0.1:8768/api/status")
        data = json.loads(req.read().decode())
        assert data["state"] == "STUDY"
        assert data["remaining_seconds"] == 1200

        # Action endpoint
        post_data = json.dumps({"action": "START_STUDY", "duration_minutes": 50}).encode()
        post_req = urllib.request.Request(
            "http://127.0.0.1:8768/api/action",
            data=post_data,
            headers={"Content-Type": "application/json"}
        )
        action_resp = json.loads(urllib.request.urlopen(post_req).read().decode())
        assert action_resp["success"] is True
    finally:
        mgr.stop()


def test_settings_dialog_blocked_sites(qapp, tmp_path):
    cfg_file = tmp_path / "test_sites_config.json"
    mgr = ConfigManager(config_path=cfg_file)

    dlg = SettingsDialog(mgr)
    assert dlg.site_list.count() >= 5
    assert "instagram.com" in [dlg.site_list.item(i).text() for i in range(dlg.site_list.count())]
    assert "youtube.com" in [dlg.site_list.item(i).text() for i in range(dlg.site_list.count())]

    # Add a new site
    dlg.edit_site.setText("https://www.pinterest.com/feed")
    dlg._add_site()
    all_sites = [dlg.site_list.item(i).text() for i in range(dlg.site_list.count())]
    assert "pinterest.com" in all_sites

    # Save values
    dlg._save_values()
    assert "pinterest.com" in mgr.get("blocked_sites")
