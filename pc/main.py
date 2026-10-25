"""
Main entry point for Lockin-Inator PC Focus Assistant.
"""
import sys
from pathlib import Path
from PyQt6 import QtWidgets, QtGui, QtCore

# Add parent to path for package imports
pkg_dir = Path(__file__).resolve().parent
if str(pkg_dir.parent) not in sys.path:
    sys.path.insert(0, str(pkg_dir.parent))

from pc.tray_app import LockinInatorPC


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")

    # Set application icon
    logo_path = pkg_dir / "assets" / "lockin_logo.png"
    if logo_path.exists():
        app.setWindowIcon(QtGui.QIcon(str(logo_path)))

    controller = LockinInatorPC(app)

    # Optional: start study session right away if run with --start flag
    if "--start" in sys.argv:
        controller.start_study_session()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
