"""
Main entry point for Lockin-Inator PC Focus Assistant.
"""
import sys
import logging
from pathlib import Path
from PyQt6 import QtWidgets, QtGui, QtCore, QtNetwork

# Setup crash logging
log_dir = Path.home() / ".lockininator"
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(log_dir / "pc_runtime.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def exception_handler(exc_type, exc_value, exc_traceback):
    logging.error("Uncaught exception in Lockin-Inator:", exc_info=(exc_type, exc_value, exc_traceback))
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = exception_handler

# Add parent to path for package imports
pkg_dir = Path(__file__).resolve().parent
if str(pkg_dir.parent) not in sys.path:
    sys.path.insert(0, str(pkg_dir.parent))

from pc.tray_app import LockinInatorPC


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")

    # Single-instance enforcement: prevent multiple conflicting instances
    server_name = "lockin_inator_single_instance_ipc"
    client_socket = QtNetwork.QLocalSocket()
    client_socket.connectToServer(server_name)
    if client_socket.waitForConnected(300):
        # Already running: notify existing instance to show dashboard and exit
        client_socket.write(b"SHOW\n")
        client_socket.flush()
        client_socket.waitForBytesWritten(300)
        client_socket.disconnectFromServer()
        sys.exit(0)

    # Start single instance IPC server
    ipc_server = QtNetwork.QLocalServer()
    ipc_server.removeServer(server_name)
    ipc_server.listen(server_name)

    # Set application icon
    logo_path = pkg_dir / "assets" / "lockin_logo.png"
    if logo_path.exists():
        app.setWindowIcon(QtGui.QIcon(str(logo_path)))

    controller = LockinInatorPC(app)

    def handle_incoming_ipc():
        conn = ipc_server.nextPendingConnection()
        if conn:
            conn.readyRead.connect(lambda: controller.show_dashboard())

    ipc_server.newConnection.connect(handle_incoming_ipc)

    # Always show dashboard window so the user sees the app is open
    controller.show_dashboard()

    # Optional: start study session right away if run with --start flag
    if "--start" in sys.argv:
        controller.start_study_session()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
