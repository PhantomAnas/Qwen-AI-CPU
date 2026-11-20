"""Qwen AI CPU — Local Chat Launcher.

A small PyQt6 app that starts llama.cpp's llama-server with a GGUF model, shows a loading popup until the model is
ready, then opens the built-in chat web UI in the default browser. Settings (model path, threads, context, thinking,
port, RAM guard) are saved to settings.json next to the exe. Errors are always shown, never hidden.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import psutil
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QFont, QIcon, QTextCursor
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
                             QSpinBox, QVBoxLayout, QWidget)

APP_NAME = "Local Chat Launcher"
BASE = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
SETTINGS = BASE / "settings.json"
LOG = BASE / "logs" / "server.log"
DEFAULTS = {
    "model_path": str(BASE / "models" / "Qwen3.6-35B-A3B-UD-IQ3_XXS.gguf"),
    "server_exe": str(BASE / "llama" / "llama-server.exe"),
    "threads": 6, "context": 8192, "port": 8080, "thinking": False,
    "cache_ram_mb": 512, "ram_guard_mb": 2000, "open_browser": True,
}
NO_WINDOW = 0x08000000  # CREATE_NO_WINDOW

STYLE = """
QWidget { background: #15181d; color: #e6e6e6; font-size: 10pt; }
QGroupBox { border: 1px solid #2c323b; border-radius: 6px; margin-top: 12px; padding: 8px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; color: #8fb3ff; }
QLineEdit, QSpinBox, QComboBox, QPlainTextEdit { background: #1d2128; border: 1px solid #333a45; border-radius: 4px; padding: 4px; }
QPushButton { background: #2a3140; border: 1px solid #3a4456; border-radius: 5px; padding: 6px 14px; }
QPushButton:hover { background: #34405a; }
QPushButton#primary { background: #2f6fed; border-color: #2f6fed; color: white; font-weight: bold; }
QPushButton#danger { background: #7a2a2a; border-color: #8c3333; }
QPushButton:disabled { color: #777; background: #22262d; }
QProgressBar { border: 1px solid #333a45; border-radius: 4px; text-align: center; background: #1d2128; }
QProgressBar::chunk { background: #2f6fed; }
"""


def load_settings() -> dict:
    s = dict(DEFAULTS)
    if SETTINGS.exists():
        try:
            s.update(json.loads(SETTINGS.read_text(encoding="utf-8")))
        except Exception as e:  # show, don't hide
            QMessageBox.warning(None, APP_NAME, f"settings.json could not be read, using defaults.\n\n{e}")
    if not Path(s["server_exe"]).is_file() and Path(DEFAULTS["server_exe"]).is_file():
        s["server_exe"] = DEFAULTS["server_exe"]      # folder was moved -> use the bundled engine
    return s


def save_settings(s: dict) -> None:
    SETTINGS.write_text(json.dumps(s, indent=2), encoding="utf-8")


def health(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=0.8) as r:
            return r.status == 200
    except Exception:
        return False


def port_busy(port: int) -> bool:
    with socket.socket() as so:
        so.settimeout(0.3)
        return so.connect_ex(("127.0.0.1", port)) == 0


def log_tail(n: int = 25) -> str:
    try:
        return "\n".join(LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-n:])
    except Exception:
        return "(no log yet)"


class LoadingDialog(QDialog):
    """Popup shown while the model loads."""

    def __init__(self, parent, model_name: str):
        super().__init__(parent)
        self.setWindowTitle("Loading model…")
        self.setModal(True)
        self.setFixedWidth(460)
        self.t0 = time.time()
        lay = QVBoxLayout(self)
        title = QLabel(f"Starting <b>{model_name}</b>")
        title.setWordWrap(True)
        self.info = QLabel("Reading the model into memory. Large models can take 10–60 s the first time.")
        self.info.setWordWrap(True)
        self.bar = QProgressBar()
        self.bar.setRange(0, 0)  # busy animation
        self.elapsed = QLabel("0 s")
        self.cancel = QPushButton("Cancel")
        lay.addWidget(title); lay.addWidget(self.info); lay.addWidget(self.bar); lay.addWidget(self.elapsed)
        lay.addWidget(self.cancel, alignment=Qt.AlignmentFlag.AlignRight)

    def tick(self, ram_mb: int):
        self.elapsed.setText(f"{time.time() - self.t0:.0f} s · model memory {ram_mb:,} MB")


class Launcher(QWidget):
    def __init__(self):
        super().__init__()
        self.s = load_settings()
        self.proc: subprocess.Popen | None = None
        self.loading: LoadingDialog | None = None
        self.log_pos = 0
        self.setWindowTitle(APP_NAME)
        self.setMinimumWidth(620)
        self._build()
        self.timer = QTimer(self, interval=1000, timeout=self._tick)
        self.timer.start()
        if port_busy(self.s["port"]) and health(self.s["port"]):
            self.status.setText(f"A model server is already running on port {self.s['port']}.")
            self._set_running(True, external=True)

    # ---------- UI
    def _build(self):
        root = QVBoxLayout(self)
        head = QLabel(APP_NAME)
        head.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        sub = QLabel("Runs a local GGUF model with llama.cpp and opens its chat in your browser.")
        sub.setStyleSheet("color:#9aa4b2")
        root.addWidget(head); root.addWidget(sub)

        g = QGroupBox("Model")
        f = QFormLayout(g)
        self.model = QLineEdit(self.s["model_path"])
        b1 = QPushButton("Browse…"); b1.clicked.connect(self._pick_model)
        r1 = QHBoxLayout(); r1.addWidget(self.model); r1.addWidget(b1)
        self.server = QLineEdit(self.s["server_exe"])
        b2 = QPushButton("Browse…"); b2.clicked.connect(self._pick_server)
        r2 = QHBoxLayout(); r2.addWidget(self.server); r2.addWidget(b2)
        f.addRow("Model file (.gguf)", r1)
        f.addRow("llama-server.exe", r2)
        root.addWidget(g)

        g2 = QGroupBox("Settings")
        f2 = QFormLayout(g2)
        self.threads = QSpinBox(); self.threads.setRange(1, os.cpu_count() or 16); self.threads.setValue(self.s["threads"])
        self.ctx = QComboBox(); [self.ctx.addItem(str(c)) for c in (4096, 8192, 16384, 32768)]
        self.ctx.setCurrentText(str(self.s["context"]))
        self.port = QSpinBox(); self.port.setRange(1024, 65535); self.port.setValue(self.s["port"])
        self.think = QCheckBox("Thinking mode (better reasoning, much slower)"); self.think.setChecked(self.s["thinking"])
        self.cram = QSpinBox(); self.cram.setRange(0, 16384); self.cram.setSuffix(" MB"); self.cram.setValue(self.s["cache_ram_mb"])
        self.cram.setToolTip("Prompt cache in RAM. Keep small (512): the 8 GB default slowly eats all memory.")
        self.guard = QSpinBox(); self.guard.setRange(0, 16000); self.guard.setSuffix(" MB"); self.guard.setValue(self.s["ram_guard_mb"])
        self.guard.setToolTip("Stop the model automatically if free RAM drops below this (0 = off).")
        self.openb = QCheckBox("Open chat in browser when ready"); self.openb.setChecked(self.s["open_browser"])
        f2.addRow("CPU threads", self.threads)
        f2.addRow("Context (tokens)", self.ctx)
        f2.addRow("Port", self.port)
        f2.addRow("Prompt cache limit", self.cram)
        f2.addRow("RAM guard (stop below)", self.guard)
        f2.addRow("", self.think)
        f2.addRow("", self.openb)
        root.addWidget(g2)

        btns = QHBoxLayout()
        self.start_b = QPushButton("Start model"); self.start_b.setObjectName("primary"); self.start_b.clicked.connect(self.start)
        self.open_b = QPushButton("Open chat"); self.open_b.clicked.connect(self.open_chat)
        self.stop_b = QPushButton("Stop model"); self.stop_b.setObjectName("danger"); self.stop_b.clicked.connect(self.stop)
        self.log_b = QPushButton("Show log"); self.log_b.setCheckable(True); self.log_b.toggled.connect(lambda on: self.logv.setVisible(on))
        for b in (self.start_b, self.open_b, self.stop_b):
            btns.addWidget(b)
        btns.addStretch(1); btns.addWidget(self.log_b)
        root.addLayout(btns)

        self.status = QLabel("Stopped.")
        self.res = QLabel("")
        self.res.setStyleSheet("color:#9aa4b2")
        root.addWidget(self.status); root.addWidget(self.res)
        self.logv = QPlainTextEdit(); self.logv.setReadOnly(True); self.logv.setVisible(False); self.logv.setMinimumHeight(180)
        self.logv.setFont(QFont("Consolas", 9))
        root.addWidget(self.logv)
        self._set_running(False)

    def _pick_model(self):
        p, _ = QFileDialog.getOpenFileName(self, "Choose model", str(Path(self.model.text()).parent), "GGUF model (*.gguf)")
        if p:
            self.model.setText(p)

    def _pick_server(self):
        p, _ = QFileDialog.getOpenFileName(self, "Choose llama-server.exe", str(Path(self.server.text()).parent), "llama-server (llama-server.exe)")
        if p:
            self.server.setText(p)

    def _collect(self) -> dict:
        self.s.update(model_path=self.model.text().strip(), server_exe=self.server.text().strip(), threads=self.threads.value(),
                      context=int(self.ctx.currentText()), port=self.port.value(), thinking=self.think.isChecked(),
                      cache_ram_mb=self.cram.value(), ram_guard_mb=self.guard.value(), open_browser=self.openb.isChecked())
        return self.s

    def _set_running(self, on: bool, external: bool = False):
        self.start_b.setEnabled(not on)
        self.stop_b.setEnabled(on and not external)
        self.open_b.setEnabled(on)
        for w in (self.model, self.server, self.threads, self.ctx, self.port, self.think, self.cram):
            w.setEnabled(not on)

    # ---------- actions
    def start(self):
        s = self._collect()
        model, exe = Path(s["model_path"]), Path(s["server_exe"])
        if not model.is_file():
            return QMessageBox.critical(self, APP_NAME, f"Model file not found:\n{model}")
        if not exe.is_file():
            return QMessageBox.critical(self, APP_NAME, f"llama-server.exe not found:\n{exe}")
        if port_busy(s["port"]):
            return QMessageBox.critical(self, APP_NAME, f"Port {s['port']} is already in use. Choose another port or stop the other program.")
        need = model.stat().st_size // 2**20 + 1500
        free = psutil.virtual_memory().available // 2**20
        if free < need and QMessageBox.question(
                self, APP_NAME, f"Only {free:,} MB RAM free; this model needs about {need:,} MB.\n"
                f"Close other apps first. Start anyway?") != QMessageBox.StandardButton.Yes:
            return
        if "--selftest" not in sys.argv:
            save_settings(s)
        LOG.parent.mkdir(exist_ok=True)
        LOG.write_text("", encoding="utf-8")
        self.log_pos = 0
        args = [str(exe), "-m", str(model), "-c", str(s["context"]), "-t", str(s["threads"]), "--host", "127.0.0.1",
                "--port", str(s["port"]), "--jinja", "-np", "1", "--cache-ram", str(s["cache_ram_mb"]),
                "--chat-template-kwargs", json.dumps({"enable_thinking": bool(s["thinking"])}), "--log-file", str(LOG)]
        try:
            self.proc = subprocess.Popen(args, cwd=str(exe.parent), creationflags=NO_WINDOW,
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            return QMessageBox.critical(self, APP_NAME, f"Could not start llama-server:\n{e}")
        self._set_running(True)
        self.status.setText("Loading model…")
        self.loading = LoadingDialog(self, model.name)
        self.loading.cancel.clicked.connect(self._cancel_loading)
        self.loading.show()

    def _cancel_loading(self):
        self.stop()

    def open_chat(self):
        QDesktopServices.openUrl(QUrl(f"http://127.0.0.1:{self.s['port']}"))

    def stop(self, quiet: bool = False):
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
            try:
                self.proc.wait(5)
            except Exception:
                pass
        self.proc = None
        if self.loading:
            self.loading.close(); self.loading = None
        self._set_running(False)
        self.status.setText("Stopped. Memory freed.")

    # ---------- timer: health, RAM, log, crashes
    def _tick(self):
        vm = psutil.virtual_memory()
        mem = 0
        if self.proc and self.proc.poll() is None:
            try:
                mem = psutil.Process(self.proc.pid).memory_info().rss // 2**20
            except Exception:
                pass
        self.res.setText(f"RAM used {vm.percent:.0f}% · free {vm.available // 2**20:,} MB · model {mem:,} MB · CPU {psutil.cpu_percent():.0f}%")
        self._read_log()
        if self.proc is None:
            return
        code = self.proc.poll()
        if code is not None:  # crashed / exited
            self.proc = None
            if self.loading:
                self.loading.close(); self.loading = None
            self._set_running(False)
            self.status.setText(f"Model server stopped unexpectedly (exit code {code}).")
            QMessageBox.critical(self, APP_NAME, f"The model server stopped (exit code {code}).\n\nLast log lines:\n{log_tail()}")
            return
        guard = self.s.get("ram_guard_mb", 0)
        if guard and vm.available // 2**20 < guard:
            self.stop()
            QMessageBox.warning(self, APP_NAME, f"Free RAM fell below {guard} MB, so the model was stopped to protect your PC.")
            return
        if self.loading:
            self.loading.tick(mem)
            if health(self.s["port"]):
                secs = time.time() - self.loading.t0
                self.loading.close(); self.loading = None
                self.status.setText(f"Ready ({secs:.0f} s) — chat at http://127.0.0.1:{self.s['port']}  · thinking {'ON' if self.s['thinking'] else 'OFF'}")
                if self.s["open_browser"]:
                    self.open_chat()

    def _read_log(self):
        if not self.logv.isVisible() or not LOG.exists():
            return
        try:
            with open(LOG, "r", encoding="utf-8", errors="replace") as fh:
                fh.seek(self.log_pos)
                new = fh.read()
                self.log_pos = fh.tell()
            if new:
                self.logv.moveCursor(QTextCursor.MoveOperation.End)
                self.logv.insertPlainText(new)
                self.logv.moveCursor(QTextCursor.MoveOperation.End)
        except Exception as e:
            self.logv.appendPlainText(f"[log read error] {e}")

    def closeEvent(self, ev):
        if self.proc and self.proc.poll() is None:
            r = QMessageBox.question(self, APP_NAME, "Stop the model and free its memory before closing?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
            if r == QMessageBox.StandardButton.Cancel:
                return ev.ignore()
            if r == QMessageBox.StandardButton.Yes:
                self.stop()
        if "--selftest" not in sys.argv:
            self._collect(); save_settings(self.s)
        ev.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    ico = BASE / "app.ico"
    if ico.exists():
        app.setWindowIcon(QIcon(str(ico)))
    w = Launcher()
    w.show()
    if "--autostart" in sys.argv and w.start_b.isEnabled():
        QTimer.singleShot(300, w.start)
    if "--selftest" in sys.argv:          # start, wait until ready (max 3 min), stop, quit; result in logs/selftest.txt
        w.s["open_browser"] = False; w.openb.setChecked(False)
        QTimer.singleShot(300, w.start)
        t0 = time.time()

        def check():
            ready = w.status.text().startswith("Ready")
            if ready or time.time() - t0 > 180:
                (BASE / "logs").mkdir(exist_ok=True)
                (BASE / "logs" / "selftest.txt").write_text(f"{'PASS' if ready else 'FAIL'} | {w.status.text()} | {w.res.text()}", encoding="utf-8")
                w.stop(); app.quit()
            else:
                QTimer.singleShot(1000, check)
        QTimer.singleShot(1500, check)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
