"""Desktop launcher for DR-TBAtlas.

Starts the Dash server on this computer, opens it in the default web browser
and shows a small window to reopen or stop it. This is the entry point of the
standalone executables built from ``packaging/drtbatlas.spec``; running
``python launcher.py`` from a source checkout works too.
"""

import os
import queue
import sys
import threading
import traceback
import webbrowser

APP_NAME = "DR-TBAtlas"
HOST = "127.0.0.1"
PREFERRED_PORT = 8050
FROZEN = getattr(sys, "frozen", False)


def user_cache_dir() -> str:
    """Per-user folder for generated tracks and the log file."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Caches")
    else:
        base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return os.path.join(base, APP_NAME)


def redirect_output_to_log() -> str:
    """Windowed executables have no console, so stdout and stderr go to a file."""
    cache_dir = user_cache_dir()
    os.makedirs(cache_dir, exist_ok=True)
    log_path = os.path.join(cache_dir, "launcher.log")
    if sys.stdout is None or sys.stderr is None:
        log = open(log_path, "w", encoding="utf-8", buffering=1)
        sys.stdout = sys.stdout or log
        sys.stderr = sys.stderr or log
    return log_path


def start_server():
    """Load the app and serve it in a background thread; returns (server, url)."""
    if FROZEN:
        os.environ.setdefault(
            "DRTBATLAS_TRACKS_DIR", os.path.join(user_cache_dir(), "tracks")
        )

    from werkzeug.serving import make_server

    import app  # loads the catalogue and builds the genome browser tracks

    try:
        server = make_server(HOST, PREFERRED_PORT, app.server, threaded=True)
    except OSError:
        # 8050 is taken (another copy, or a dev server): use any free port.
        server = make_server(HOST, 0, app.server, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://{HOST}:{server.server_port}/"


class LauncherWindow:
    """A small control window: status, the address, reopen and quit."""

    POLL_MS = 200

    def __init__(self, root, log_path: str):
        import tkinter as tk
        from tkinter import font, ttk

        self.root = root
        self.log_path = log_path
        self.server = None
        self.url = None
        self.events: "queue.Queue" = queue.Queue()

        root.title(APP_NAME)
        root.resizable(False, False)
        root.protocol("WM_DELETE_WINDOW", self.quit)
        self._set_icon(tk)

        frame = ttk.Frame(root, padding=20)
        frame.grid()
        title_font = font.nametofont("TkDefaultFont").copy()
        title_font.configure(size=16, weight="bold")
        ttk.Label(frame, text=APP_NAME, font=title_font).grid(
            row=0, column=0, columnspan=2, pady=(0, 8)
        )
        self.status = ttk.Label(
            frame,
            text=(
                "Starting, please wait...\n"
                "The first start takes longer while the genome\n"
                "browser tracks are prepared."
            ),
            justify="center",
        )
        self.status.grid(row=1, column=0, columnspan=2, pady=(0, 12))
        self.open_button = ttk.Button(
            frame, text="Open in browser", command=self.open_browser, state="disabled"
        )
        self.open_button.grid(row=2, column=0, padx=4)
        ttk.Button(frame, text="Quit", command=self.quit).grid(row=2, column=1, padx=4)

        threading.Thread(target=self._start, daemon=True).start()
        root.after(self.POLL_MS, self._poll)

    def _set_icon(self, tk) -> None:
        icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.png")
        try:
            self._icon = tk.PhotoImage(file=icon)
            self.root.iconphoto(True, self._icon)
        except tk.TclError:
            pass

    def _start(self) -> None:
        # Runs off the main thread; tkinter is only touched from _poll.
        try:
            self.events.put(("ready", start_server()))
        except Exception:
            traceback.print_exc()
            self.events.put(("failed", None))

    def _poll(self) -> None:
        try:
            kind, payload = self.events.get_nowait()
        except queue.Empty:
            self.root.after(self.POLL_MS, self._poll)
            return
        if kind == "ready":
            self.server, self.url = payload
            self.status.config(
                text=(
                    f"Running at {self.url}\n\n"
                    "Keep this window open while you use DR-TBAtlas.\n"
                    "Click Quit to stop it."
                )
            )
            self.open_button.config(state="normal")
            self.open_browser()
        else:
            self.status.config(
                text=f"DR-TBAtlas could not start.\nDetails were saved to:\n{self.log_path}"
            )

    def open_browser(self) -> None:
        if self.url:
            webbrowser.open(self.url)

    def quit(self) -> None:
        if self.server is not None:
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        self.root.destroy()


def run_in_console() -> None:
    """Fallback when no graphical display is available."""
    print("Starting DR-TBAtlas, please wait...")
    server, url = start_server()
    print(f"DR-TBAtlas is running at {url}\nPress Ctrl+C to stop it.")
    webbrowser.open(url)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.shutdown()


def main() -> None:
    log_path = redirect_output_to_log()
    try:
        import tkinter as tk

        root = tk.Tk()
    except Exception:
        run_in_console()
        return
    LauncherWindow(root, log_path)
    root.mainloop()


if __name__ == "__main__":
    main()
