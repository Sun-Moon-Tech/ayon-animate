"""Script wraps launch mechanism of Photoshop implementations.

Arguments passed to the script are passed to launch function in host
implementation. In all cases requires host app executable and may contain
workfile or others.
"""

import os
import sys
from pathlib import Path
import logging
import traceback

LOG_DIR = str(Path.home()) + "/.ayon"
LOG_PATH = os.path.join(LOG_DIR, "ayon_animate_python.log")

class _TeeStream:
    def __init__(self, original, log_file):
        self._original = original
        self._log_file = log_file

    def write(self, message):
        if self._original:
            self._original.write(message)
        self._log_file.write(message)

    def flush(self):
        if self._original:
            self._original.flush()
        self._log_file.flush()


def _setup_file_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = open(LOG_PATH, "a", encoding="utf-8")

    # Mirror all console output to file while preserving current behavior.
    sys.stdout = _TeeStream(sys.stdout, log_file)
    sys.stderr = _TeeStream(sys.stderr, log_file)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    if not any(
        isinstance(handler, logging.FileHandler)
        and getattr(handler, "baseFilename", "") == os.path.abspath(LOG_PATH)
        for handler in root_logger.handlers
    ):
        file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        root_logger.addHandler(file_handler)

    return log_file


_LOG_FILE_HANDLE = _setup_file_logging()

try:
    from ayon_animate.api.lib import main as host_main
except Exception as e:
    print(f"[AYON ANIMATE] FATAL: Failed to import ayon_animate.api.lib: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)

# Get current file to locate start point of sys.argv
CURRENT_FILE = os.path.abspath(__file__)


def debug_msgbox(title, message):
    """Show a debug message box - useful when stdout is not available."""
    try:
        from qtpy import QtWidgets, QtCore
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication([])
        
        msgbox = QtWidgets.QMessageBox()
        msgbox.setWindowTitle(title)
        msgbox.setText(message)
        msgbox.setWindowModality(QtCore.Qt.ApplicationModal)
        msgbox.exec_()  # Block until user clicks OK
        return True
    except Exception as e:
        print(f"Could not show msgbox: {e}", flush=True)
        return False


def show_error_messagebox(title, message, detail_message=None):
    """Function will show message and process ends after closing it."""
    from qtpy import QtWidgets, QtCore
    from ayon_core import style

    app = QtWidgets.QApplication([])
    app.setStyleSheet(style.load_stylesheet())

    msgbox = QtWidgets.QMessageBox()
    msgbox.setWindowTitle(title)
    msgbox.setText(message)

    if detail_message:
        msgbox.setDetailedText(detail_message)

    msgbox.setWindowModality(QtCore.Qt.ApplicationModal)
    msgbox.show()

    sys.exit(app.exec_())


def on_invalid_args(script_not_found):
    """Show to user message box saying that something went wrong.

    Tell user that arguments to launch implementation are invalid with
    arguments details.

    Args:
        script_not_found (bool): Use different message based on this value.
    """

    title = "Invalid arguments"
    joined_args = ", ".join("\"{}\"".format(arg) for arg in sys.argv)
    if script_not_found:
        submsg = "Where couldn't find script path:\n\"{}\""
    else:
        submsg = "Expected Host executable after script path:\n\"{}\""

    message = "BUG: Got invalid arguments so can't launch Host application."
    detail_message = "Process was launched with arguments:\n{}\n\n{}".format(
        joined_args,
        submsg.format(CURRENT_FILE)
    )

    show_error_messagebox(title, message, detail_message)


def main(argv):
    try:
        print("[AYON ANIMATE] Launch script starting", flush=True)
        # Modify current file path to find match in sys.argv which may be different
        #   on windows (different letter cases and slashes).
        modified_current_file = CURRENT_FILE.replace("\\", "/").lower()

        # Create a copy of sys argv
        sys_args = list(argv)
        print(f"[AYON ANIMATE] sys.argv = {sys_args}", flush=True)
        # debug_msgbox("Debug Info", f"sys.argv: {sys_args}")
        
        after_script_idx = None
        # Find script path in sys.argv to know index of argv where host
        #   executable should be.
        for idx, item in enumerate(sys_args):
            if item.replace("\\", "/").lower() == modified_current_file:
                after_script_idx = idx + 1
                break

        # Validate that there is at least one argument after script path
        launch_args = None
        if after_script_idx is not None:
            launch_args = sys_args[after_script_idx:]
                    
        print(f"[AYON ANIMATE] Launch args = {launch_args}", flush=True)
        # debug_msgbox("Debug Info", f"Launch args: {launch_args}")

        if launch_args:
            # Launch host implementation
            print(f"[AYON ANIMATE] Calling host_main with args: {launch_args}", flush=True)
            host_main(*launch_args)
        else:
            # Show message box
            print(f"[AYON ANIMATE] Invalid args - after_script_idx={after_script_idx}", flush=True)
            on_invalid_args(after_script_idx is None)
    except Exception as e:
        print(f"[AYON ANIMATE] ERROR in main(): {e}", flush=True)
        traceback.print_exc()
        raise

if __name__ == "__main__":
    try:
        print("[AYON ANIMATE] Script entry point", flush=True)
        main(sys.argv)
    except Exception as e:
        print(f"[AYON ANIMATE] FATAL: Uncaught exception in main(): {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)
