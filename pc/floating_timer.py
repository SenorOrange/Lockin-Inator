"""
Floating Timer Widget for Lockin-Inator PC.
A sleek, draggable, always-on-top pill widget displayed on-screen during
Study and Break sessions, keeping the live timer visible without being distracting.
Includes optional Physics Mode with screen bouncing, momentum sliding, friction deceleration,
jiggle impact effects, and hold-to-stop physics that automatically reverts to normal 1.0x size.
"""
import math
import random
import time
from pathlib import Path
from PyQt6 import QtCore, QtGui, QtWidgets

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
LOGO_PATH = ASSETS_DIR / "lockin_logo.png"


class FloatingTimerWidget(QtWidgets.QWidget):
    lock_in_early_signal = QtCore.pyqtSignal()
    open_dashboard_signal = QtCore.pyqtSignal()
    end_session_signal = QtCore.pyqtSignal()
    physics_toggled_signal = QtCore.pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = "IDLE"
        self._drag_pos = None
        self._is_moved_by_user = False

        # Physics state & settings
        self._settings = QtCore.QSettings("LockinInator", "FloatingTimer")
        self.physics_enabled = self._settings.value("physics_enabled", False, type=bool)

        self.scale_factor = 1.0  # Starts at 1.0; blooms to 1.5x during active physics movement
        self.vx = 0.0
        self.vy = 0.0
        self._pos_x = 0.0
        self._pos_y = 0.0
        self._is_held = False
        self._drag_samples = []
        self._jiggle_frames = 0
        self._jiggle_offset_y = 0.0

        # Physics simulation timer (60 FPS)
        self._physics_timer = QtCore.QTimer(self)
        self._physics_timer.setInterval(16)
        self._physics_timer.timeout.connect(self._on_physics_tick)

        self._setup_ui()
        if self.physics_enabled:
            self._physics_timer.start()

    def _setup_ui(self):
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
            | QtCore.Qt.WindowType.Tool
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._apply_dimensions()

        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.main_layout.setContentsMargins(4, 4, 4, 4)
        self.main_layout.setSpacing(0)

        # Background frame (Pill)
        self.frame = QtWidgets.QFrame(self)
        self.frame.setObjectName("pillFrame")

        self.frame_layout = QtWidgets.QHBoxLayout(self.frame)
        self._apply_frame_layout_margins()
        self.frame_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # Icon / Status Emoji
        self.icon_label = QtWidgets.QLabel("🔒", self.frame)
        self.frame_layout.addWidget(self.icon_label)

        # Digital Countdown Label
        self.timer_label = QtWidgets.QLabel("50:00", self.frame)
        self.frame_layout.addWidget(self.timer_label)

        # Break Action Button ("Lock In") - hidden during study
        self.btn_lock_in = QtWidgets.QPushButton("Lock In", self.frame)
        self.btn_lock_in.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_lock_in.setVisible(False)
        self.btn_lock_in.clicked.connect(self.lock_in_early_signal.emit)
        self.frame_layout.addWidget(self.btn_lock_in)

        self.main_layout.addWidget(self.frame)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.OpenHandCursor))
        self._update_styles()

    def _set_scale(self, scale: float):
        """Smoothly scale between normal (1.0x) and physics (1.5x) while maintaining center point."""
        if abs(self.scale_factor - scale) < 0.01:
            return

        old_center = self.geometry().center()
        self.scale_factor = scale
        self._apply_dimensions()
        self._apply_frame_layout_margins()
        self._update_styles()

        new_x = old_center.x() - self.width() // 2
        new_y = old_center.y() - self.height() // 2
        self._pos_x = float(new_x)
        self._pos_y = float(new_y)
        self.move(new_x, new_y)

    def _apply_dimensions(self):
        sf = self.scale_factor
        h = int(46 * sf)
        self.setFixedHeight(h)
        if self.state == "BREAK":
            w = int(240 * sf)
        else:
            w = int(170 * sf)
        self.setFixedWidth(w)

    def _apply_frame_layout_margins(self):
        sf = self.scale_factor
        h_pad = int(12 * sf)
        v_pad = int(4 * sf)
        spacing = int(8 * sf)
        self.frame_layout.setContentsMargins(h_pad, v_pad, h_pad, v_pad)
        self.frame_layout.setSpacing(spacing)

    def _update_styles(self):
        sf = self.scale_factor
        border_radius = int(19 * sf)
        timer_font_size = int(16 * sf)
        icon_font_size = int(15 * sf)
        btn_font_size = int(11 * sf)
        btn_pad_v = int(4 * sf)
        btn_pad_h = int(10 * sf)
        btn_radius = int(10 * sf)

        self.icon_label.setStyleSheet(f"font-size: {icon_font_size}px;")

        if self.state == "BREAK":
            border_color = "#10b981"
            timer_color = "#10b981"
            self.icon_label.setText("☕")
            self.btn_lock_in.setVisible(True)
        else:
            border_color = "#38bdf8"
            timer_color = "#38bdf8"
            self.icon_label.setText("🔒")
            self.btn_lock_in.setVisible(False)

        self.frame.setStyleSheet(f"""
            QFrame#pillFrame {{
                background-color: rgba(15, 23, 42, 0.94);
                border: 2px solid {border_color};
                border-radius: {border_radius}px;
            }}
        """)

        self.timer_label.setStyleSheet(f"""
            color: {timer_color};
            font-size: {timer_font_size}px;
            font-weight: 800;
            font-family: Consolas, monospace;
            letter-spacing: 1px;
        """)

        self.btn_lock_in.setStyleSheet(f"""
            QPushButton {{
                background-color: #059669;
                color: #ffffff;
                border: none;
                border-radius: {btn_radius}px;
                padding: {btn_pad_v}px {btn_pad_h}px;
                font-size: {btn_font_size}px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: #047857;
            }}
        """)

    def set_physics_enabled(self, enabled: bool):
        self.physics_enabled = bool(enabled)
        self._settings.setValue("physics_enabled", self.physics_enabled)

        if self.physics_enabled:
            # When physics is first turned on, kick off with a natural glide
            self.vx = 4.5
            self.vy = 3.2
            self._set_scale(1.5)
            self._pos_x = float(self.x())
            self._pos_y = float(self.y())
            if self.isVisible():
                self._physics_timer.start()
        else:
            self._physics_timer.stop()
            self.vx = 0.0
            self.vy = 0.0
            self._jiggle_frames = 0
            self._set_scale(1.0)
            self._keep_within_current_screen()

        self.physics_toggled_signal.emit(self.physics_enabled)

    def _keep_within_current_screen(self):
        screen = QtGui.QGuiApplication.screenAt(self.geometry().center())
        if not screen:
            screen = QtGui.QGuiApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            new_x = max(geo.left(), min(self.x(), geo.right() - self.width()))
            new_y = max(geo.top(), min(self.y(), geo.bottom() - self.height()))
            self._pos_x = float(new_x)
            self._pos_y = float(new_y)
            self.move(new_x, new_y)

    def _on_physics_tick(self):
        if not self.physics_enabled or self._is_held or not self.isVisible():
            return

        # Jiggle decay
        if self._jiggle_frames > 0:
            self._jiggle_frames -= 1
            self._jiggle_offset_y = math.sin(self._jiggle_frames * 0.9) * 3.0
        else:
            self._jiggle_offset_y = 0.0

        current_speed = math.hypot(self.vx, self.vy)

        # Natural deceleration / friction model:
        # Loses ~1.2% speed per frame, sliding naturally across the monitor and smoothly stopping
        if current_speed > 0.18:
            # Active movement -> maintain 1.5x scale
            if abs(self.scale_factor - 1.5) > 0.01:
                self._set_scale(1.5)

            friction = 0.988
            self.vx *= friction
            self.vy *= friction

            # Advance position
            self._pos_x += self.vx
            self._pos_y += self.vy

            center_pt = QtCore.QPoint(int(self._pos_x + self.width() / 2), int(self._pos_y + self.height() / 2))
            screen = QtGui.QGuiApplication.screenAt(center_pt)
            if not screen:
                screen = QtGui.QGuiApplication.primaryScreen()

            if screen:
                geo = screen.availableGeometry()
                bounced = False
                restitution = 0.75  # Absorbs 25% energy on wall impact

                if self._pos_x < geo.left():
                    self._pos_x = float(geo.left())
                    self.vx = abs(self.vx) * restitution + random.uniform(-0.15, 0.15)
                    bounced = True
                elif self._pos_x + self.width() > geo.right():
                    self._pos_x = float(geo.right() - self.width())
                    self.vx = -(abs(self.vx) * restitution + random.uniform(-0.15, 0.15))
                    bounced = True

                if self._pos_y < geo.top():
                    self._pos_y = float(geo.top())
                    self.vy = abs(self.vy) * restitution + random.uniform(-0.15, 0.15)
                    bounced = True
                elif self._pos_y + self.height() > geo.bottom():
                    self._pos_y = float(geo.bottom() - self.height())
                    self.vy = -(abs(self.vy) * restitution + random.uniform(-0.15, 0.15))
                    bounced = True

                if bounced:
                    self._trigger_jiggle()

            self.move(int(self._pos_x), int(self._pos_y + self._jiggle_offset_y))

        else:
            # Speed is near zero -> coast to a full stop and revert to normal 1.0x size!
            self.vx = 0.0
            self.vy = 0.0
            if abs(self.scale_factor - 1.0) > 0.01:
                self._set_scale(1.0)

            if self._jiggle_frames > 0:
                self.move(int(self._pos_x), int(self._pos_y + self._jiggle_offset_y))

    def _trigger_jiggle(self):
        self._jiggle_frames = 10

    def _kickstart_physics(self):
        """Fling the widget into motion at 1.5x size."""
        angle = random.uniform(0.2, math.pi * 1.8)
        speed = 8.0
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self._set_scale(1.5)
        self._trigger_jiggle()

    def show_widget(self, state: str, remaining_seconds: int):
        self.state = state
        self.update_timer(remaining_seconds)
        self._apply_dimensions()
        self._apply_frame_layout_margins()
        self._update_styles()

        if not self._is_moved_by_user:
            screen = QtGui.QGuiApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                self._pos_x = float(geo.width() - self.width() - 30)
                self._pos_y = 30.0
                self.move(int(self._pos_x), int(self._pos_y))
        else:
            self._pos_x = float(self.x())
            self._pos_y = float(self.y())

        self.show()
        self.raise_()

        if self.physics_enabled and not self._physics_timer.isActive():
            self._physics_timer.start()

    def update_timer(self, remaining_seconds: int):
        mins, secs = divmod(max(0, remaining_seconds), 60)
        self.timer_label.setText(f"{mins:02d}:{secs:02d}")

    def showEvent(self, event):
        super().showEvent(event)
        if self.physics_enabled and not self._physics_timer.isActive():
            self._physics_timer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._physics_timer.stop()

    # Dragging & Throwing Mechanics
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._is_held = True
            now = time.time()
            self._drag_samples = [(now, event.globalPosition().toPoint())]
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ClosedHandCursor))
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.MouseButton.LeftButton and self._drag_pos:
            target_pos = event.globalPosition().toPoint() - self._drag_pos
            self.move(target_pos)
            self._pos_x = float(target_pos.x())
            self._pos_y = float(target_pos.y())
            self._is_moved_by_user = True

            now = time.time()
            self._drag_samples.append((now, event.globalPosition().toPoint()))
            self._drag_samples = [(t, p) for t, p in self._drag_samples if now - t <= 0.25]
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.OpenHandCursor))
            self._is_held = False

            if self.physics_enabled and len(self._drag_samples) >= 2:
                t_start, p_start = self._drag_samples[0]
                t_end, p_end = self._drag_samples[-1]
                dt = t_end - t_start
                dx = p_end.x() - p_start.x()
                dy = p_end.y() - p_start.y()
                dist = math.hypot(dx, dy)
                speed_px_sec = dist / max(dt, 0.001)

                # "when held still it should automatically revert back to its normal size"
                if dt >= 0.08 and speed_px_sec < 90.0:
                    self.vx = 0.0
                    self.vy = 0.0
                    self._set_scale(1.0)  # Revert immediately to normal 1.0x size!
                elif speed_px_sec >= 90.0:
                    # User threw/flung the widget -> impart velocity & expand to 1.5x size!
                    scale = 1.0 / (dt * 60.0)
                    self.vx = max(-14.0, min(14.0, dx * scale))
                    self.vy = max(-14.0, min(14.0, dy * scale))
                    self._set_scale(1.5)
                    self._trigger_jiggle()
            elif self.physics_enabled and len(self._drag_samples) < 2:
                # Simple click without movement: revert to 1.0x normal size
                self.vx = 0.0
                self.vy = 0.0
                self._set_scale(1.0)

            self._drag_samples.clear()
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

        menu.addSeparator()

        action_physics = menu.addAction("⚽ Physics Mode (Bouncing, Friction & 1.5x)")
        action_physics.setCheckable(True)
        action_physics.setChecked(self.physics_enabled)
        action_physics.toggled.connect(self.set_physics_enabled)

        if self.physics_enabled:
            action_kick = menu.addAction("🚀 Fling / Nudge Widget")
            action_kick.triggered.connect(self._kickstart_physics)

        if self.state in ("STUDY", "BREAK"):
            menu.addSeparator()
            action_end = menu.addAction("🛑 End Study Session...")
            action_end.triggered.connect(self.end_session_signal.emit)

        menu.exec(event.globalPos())
