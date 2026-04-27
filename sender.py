import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import threading
import time

# ── Theme ──────────────────────────────────────────────────────────────────────
BG        = "#0d0d0d"
PANEL     = "#141414"
BORDER    = "#2a2a2a"
GREEN     = "#00ff88"
GREEN_DIM = "#00994d"
AMBER     = "#ffaa00"
AMBER_DIM = "#cc8800"
RED       = "#ff4444"
TEXT      = "#e8e8e8"
MUTED     = "#555555"
FONT_MONO = ("Courier New", 11)
FONT_UI   = ("Courier New", 10)

# ── ESP32 known VID/PID combos ─────────────────────────────────────────────────
ESP_VIDS = {
    0x10C4: "CP2102 (ESP32)",       # Silicon Labs CP2102/CP2104
    0x1A86: "CH340 (ESP32)",        # CH340/CH341 (cheap boards)
    0x303A: "ESP32-S3 Native USB",  # ESP32-S3 / S2 native USB
    0x0403: "FTDI (ESP32)",         # FTDI FT232R
    0x2341: "Arduino (ESP32)",      # Arduino-compatible
}


def find_esp32_port():
    """Return (device, description) of first likely ESP32 port, or (None, None)."""
    for p in serial.tools.list_ports.comports():
        if p.vid in ESP_VIDS:
            return p.device, f"{p.device} — {ESP_VIDS[p.vid]}"
    return None, None


class ESP32KeyboardSender:
    def __init__(self, root):
        self.root = root
        self.root.title("ESP32 BLE Keyboard Sender")
        self.root.configure(bg=BG)
        self.root.geometry("860x660")
        self.root.resizable(True, True)

        self.serial_conn = None
        self.is_typing   = False
        self.live_mode   = False
        self._port_map   = {}   # display label → actual device path

        self._build_ui()
        self._refresh_ports()

    # ── UI ─────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.TCombobox",
                         fieldbackground=PANEL, background=PANEL,
                         foreground=TEXT, bordercolor=BORDER,
                         arrowcolor=GREEN, selectbackground=PANEL,
                         selectforeground=GREEN)
        style.map("Dark.TCombobox", fieldbackground=[("readonly", PANEL)],
                  foreground=[("readonly", TEXT)])
        style.configure("Green.Horizontal.TProgressbar",
                         troughcolor=PANEL, background=GREEN,
                         bordercolor=BORDER, lightcolor=GREEN, darkcolor=GREEN)

        # ── Header ──
        hdr = tk.Frame(self.root, bg=BG)
        hdr.pack(fill="x", padx=20, pady=(16, 0))
        tk.Label(hdr, text="◈ ESP32", font=("Courier New", 18, "bold"),
                 bg=BG, fg=GREEN).pack(side="left")
        tk.Label(hdr, text=" BLE KEYBOARD SENDER", font=("Courier New", 18, "bold"),
                 bg=BG, fg=TEXT).pack(side="left")
        self.status_dot = tk.Label(hdr, text="●  DISCONNECTED",
                                    font=FONT_UI, bg=BG, fg=RED)
        self.status_dot.pack(side="right")

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", padx=20, pady=8)

        # ── Port row ──
        port_row = tk.Frame(self.root, bg=BG)
        port_row.pack(fill="x", padx=20, pady=(0, 2))

        tk.Label(port_row, text="PORT", font=("Courier New", 9, "bold"),
                 bg=BG, fg=MUTED).pack(side="left", padx=(0, 8))

        self.port_var = tk.StringVar()
        self.port_cb  = ttk.Combobox(port_row, textvariable=self.port_var,
                                      style="Dark.TCombobox", state="readonly",
                                      width=32, font=FONT_UI)
        self.port_cb.pack(side="left", padx=(0, 8))

        self._btn(port_row, "⟳ REFRESH",    self._refresh_ports,  fg=MUTED ).pack(side="left", padx=(0, 8))
        self._btn(port_row, "⚡ AUTO-DETECT", self._auto_detect,    fg=AMBER ).pack(side="left", padx=(0, 8))
        self._btn(port_row, "CONNECT",        self._connect,        fg=GREEN ).pack(side="left", padx=(0, 8))
        self._btn(port_row, "DISCONNECT",     self._disconnect,     fg=RED   ).pack(side="left")

        # ── Chip info strip (shows after auto-detect / connect) ──
        self.chip_var = tk.StringVar(value="")
        self.chip_lbl = tk.Label(self.root, textvariable=self.chip_var,
                                  font=("Courier New", 8), bg=BG, fg=AMBER, anchor="w")
        self.chip_lbl.pack(fill="x", padx=24, pady=(0, 2))

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", padx=20, pady=(4, 0))

        # ══════════════════════════════════════════════════════════════════════
        # BOTTOM — packed before editor so always visible
        # ══════════════════════════════════════════════════════════════════════

        # log
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", padx=20, side="bottom")
        self.log_var = tk.StringVar(value="● Ready.")
        tk.Label(self.root, textvariable=self.log_var, font=("Courier New", 9),
                 bg=BG, fg=MUTED, anchor="w").pack(fill="x", padx=22, pady=4, side="bottom")

        # delay row
        delay_row = tk.Frame(self.root, bg=BG)
        delay_row.pack(fill="x", padx=20, pady=(0, 4), side="bottom")
        tk.Label(delay_row, text="CHAR DELAY", font=("Courier New", 9, "bold"),
                 bg=BG, fg=MUTED).pack(side="left", padx=(0, 10))
        self.delay_var = tk.IntVar(value=50)
        self._btn(delay_row, "−", self._delay_down, fg=RED  ).pack(side="left", padx=(0, 4))
        tk.Label(delay_row, textvariable=self.delay_var,
                 font=("Courier New", 11, "bold"), bg=BG, fg=GREEN,
                 width=4, anchor="center").pack(side="left")
        tk.Label(delay_row, text="ms", font=("Courier New", 9),
                 bg=BG, fg=MUTED).pack(side="left", padx=(2, 8))
        self._btn(delay_row, "+", self._delay_up, fg=GREEN).pack(side="left", padx=(0, 12))
        tk.Scale(delay_row, from_=10, to=500, variable=self.delay_var,
                 orient="horizontal", bg=BG, fg=MUTED, troughcolor=PANEL,
                 highlightthickness=0, activebackground=GREEN,
                 showvalue=False, length=180, sliderrelief="flat",
                 sliderlength=14).pack(side="left", padx=(0, 16))
        for label, val in [("FAST 20ms", 20), ("NORMAL 50ms", 50), ("SLOW 150ms", 150)]:
            lbl = tk.Label(delay_row, text=label, font=("Courier New", 8, "bold"),
                           bg=PANEL, fg=MUTED, cursor="hand2", padx=6, pady=3)
            lbl.pack(side="left", padx=3)
            lbl.bind("<Button-1>", lambda e, v=val: self.delay_var.set(v))
            lbl.bind("<Enter>",    lambda e, w=lbl: w.configure(fg=GREEN))
            lbl.bind("<Leave>",    lambda e, w=lbl: w.configure(fg=MUTED))

        # progress bar
        self.prog_frame = tk.Frame(self.root, bg=BG)
        self.prog_frame.pack(fill="x", padx=20, pady=(0, 4), side="bottom")
        self.progress_var = tk.DoubleVar(value=0)
        self.progress = ttk.Progressbar(self.prog_frame, variable=self.progress_var,
                                         style="Green.Horizontal.TProgressbar", maximum=100)
        self.progress.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.prog_label = tk.Label(self.prog_frame, text="0 / 0 chars",
                                    font=("Courier New", 9), bg=BG, fg=MUTED)
        self.prog_label.pack(side="right")

        # action buttons
        self.btn_row = tk.Frame(self.root, bg=BG)
        self.btn_row.pack(fill="x", padx=20, pady=(0, 8), side="bottom")
        self._big_btn(self.btn_row, "⎘  PASTE", self._paste,
                      fg=TEXT, hover="#333").pack(side="left", padx=(0, 8))
        self.type_btn = self._big_btn(self.btn_row, "▶  START TYPING",
                                       self._start_typing, fg=BG, bg=GREEN, hover=GREEN_DIM)
        self.type_btn.pack(side="left", padx=(0, 8))
        self._big_btn(self.btn_row, "✕  CLEAR", self._clear,
                      fg=RED, hover="#200").pack(side="left")

        # ══════════════════════════════════════════════════════════════════════
        # MODE TOGGLE BAR
        # ══════════════════════════════════════════════════════════════════════
        mode_bar = tk.Frame(self.root, bg=PANEL)
        mode_bar.pack(fill="x", padx=20, pady=(8, 0))

        tk.Label(mode_bar, text="MODE", font=("Courier New", 9, "bold"),
                 bg=PANEL, fg=MUTED, padx=10, pady=7).pack(side="left")

        self.live_tab = tk.Label(mode_bar,
                                  text="⚡  LIVE — keystrokes sent instantly as you type",
                                  font=("Courier New", 9, "bold"),
                                  bg=PANEL, fg=MUTED, cursor="hand2", padx=14, pady=7)
        self.live_tab.pack(side="left")
        self.live_tab.bind("<Button-1>", lambda e: self._set_mode("LIVE"))

        tk.Label(mode_bar, text="|", bg=PANEL, fg=BORDER, pady=7).pack(side="left")

        self.batch_tab = tk.Label(mode_bar,
                                   text="▶  BATCH — prepare text then send all at once",
                                   font=("Courier New", 9, "bold"),
                                   bg=PANEL, fg=MUTED, cursor="hand2", padx=14, pady=7)
        self.batch_tab.pack(side="left")
        self.batch_tab.bind("<Button-1>", lambda e: self._set_mode("BATCH"))

        self.mode_indicator = tk.Label(mode_bar, text="", font=("Courier New", 8),
                                        bg=PANEL, fg=GREEN, padx=10)
        self.mode_indicator.pack(side="right")

        # ══════════════════════════════════════════════════════════════════════
        # EDITOR
        # ══════════════════════════════════════════════════════════════════════
        ed_hdr = tk.Frame(self.root, bg=BG)
        ed_hdr.pack(fill="x", padx=20, pady=(6, 3))
        tk.Label(ed_hdr, text="TEXT EDITOR", font=("Courier New", 9, "bold"),
                 bg=BG, fg=MUTED).pack(side="left")
        self.ed_hint = tk.Label(ed_hdr, text="", font=("Courier New", 9), bg=BG, fg=MUTED)
        self.ed_hint.pack(side="left", padx=6)

        editor_frame = tk.Frame(self.root, bg=BORDER)
        editor_frame.pack(fill="both", expand=True, padx=20, pady=(0, 4))
        inner = tk.Frame(editor_frame, bg=PANEL)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        self.line_nums = tk.Text(inner, width=4, bg="#111111", fg=MUTED,
                                  font=FONT_MONO, bd=0, state="disabled",
                                  selectbackground="#111111", pady=6)
        self.line_nums.pack(side="left", fill="y")
        tk.Frame(inner, bg=BORDER, width=1).pack(side="left", fill="y")

        self.editor = tk.Text(inner, bg=PANEL, fg=TEXT, font=FONT_MONO,
                               bd=0, insertbackground=GREEN, wrap="word",
                               undo=True, pady=6, padx=10,
                               selectbackground=GREEN_DIM, selectforeground=BG)
        self.editor.pack(side="left", fill="both", expand=True)

        sb = tk.Scrollbar(inner, command=self._sync_scroll, bg=PANEL,
                          troughcolor=PANEL, activebackground=GREEN)
        sb.pack(side="right", fill="y")
        self.editor.configure(yscrollcommand=sb.set)

        self.editor.bind("<KeyRelease>", self._on_key)
        self.editor.bind("<MouseWheel>", self._update_lines)
        self._update_lines()

        self._set_mode("BATCH")

    # ── Widget helpers ─────────────────────────────────────────────────────────
    def _btn(self, parent, text, cmd, fg=TEXT, active_fg=None):
        b = tk.Label(parent, text=text, font=("Courier New", 9, "bold"),
                     bg=BG, fg=fg, cursor="hand2", padx=6, pady=2)
        b.bind("<Button-1>", lambda e: cmd())
        b.bind("<Enter>",  lambda e: b.configure(fg=active_fg or TEXT))
        b.bind("<Leave>",  lambda e: b.configure(fg=fg))
        return b

    def _big_btn(self, parent, text, cmd, fg=TEXT, bg=PANEL, hover="#222"):
        f     = tk.Frame(parent, bg=BORDER)
        inner = tk.Frame(f, bg=bg)
        inner.pack(padx=1, pady=1)
        lbl = tk.Label(inner, text=text, font=("Courier New", 10, "bold"),
                       bg=bg, fg=fg, cursor="hand2", padx=16, pady=8)
        lbl.pack()
        for w in (f, inner, lbl):
            w.bind("<Button-1>", lambda e: cmd())
            w.bind("<Enter>",  lambda e: [inner.configure(bg=hover), lbl.configure(bg=hover)])
            w.bind("<Leave>",  lambda e: [inner.configure(bg=bg),    lbl.configure(bg=bg)])
        return f

    # ── Mode switching ─────────────────────────────────────────────────────────
    def _set_mode(self, mode):
        self.live_mode = (mode == "LIVE")

        if self.live_mode:
            self.live_tab.configure(fg=AMBER, bg="#1c1500")
            self.batch_tab.configure(fg=MUTED, bg=PANEL)
            self.mode_indicator.configure(text="⚡ LIVE MODE ACTIVE", fg=AMBER)
            self.ed_hint.configure(text="— every key you press is sent to ESP32 instantly")
            self.editor.configure(insertbackground=AMBER)
            self.type_btn.pack_forget()
            self.prog_frame.pack_forget()
        else:
            self.batch_tab.configure(fg=GREEN, bg="#001a0d")
            self.live_tab.configure(fg=MUTED, bg=PANEL)
            self.mode_indicator.configure(text="▶ BATCH MODE ACTIVE", fg=GREEN)
            self.ed_hint.configure(text="— prepare your text, then hit START TYPING")
            self.editor.configure(insertbackground=GREEN)
            self.prog_frame.pack(fill="x", padx=20, pady=(0, 4),
                                  side="bottom", before=self.btn_row)
            self.type_btn.pack(side="left", padx=(0, 8),
                                after=self.btn_row.winfo_children()[0])

        self._log(f"Mode: {'LIVE — type to send' if self.live_mode else 'BATCH — use START TYPING'}")

    # ── Line numbers ───────────────────────────────────────────────────────────
    def _update_lines(self, event=None):
        self.root.after(10, self.__redraw_lines)

    def __redraw_lines(self):
        lines = int(self.editor.index("end-1c").split(".")[0])
        self.line_nums.configure(state="normal")
        self.line_nums.delete("1.0", "end")
        for i in range(1, lines + 1):
            self.line_nums.insert("end", f"{i:>3}\n")
        self.line_nums.configure(state="disabled")

    def _sync_scroll(self, *args):
        self.editor.yview(*args)
        self.line_nums.yview(*args)

    # ── Key handler ────────────────────────────────────────────────────────────
    def _on_key(self, event):
        self._update_lines()
        if not self.live_mode:
            return
        if not self.serial_conn or not self.serial_conn.is_open:
            self._log("⚡ LIVE: not connected — key not sent")
            return

        keysym = event.keysym
        char   = event.char

        # Tokens below must match the command parser implemented on the ESP32 side.
        SPECIAL = {
            "Return"    : b"[ENTER]",
            "BackSpace" : b"[BACK]",
            "Tab"       : b"[TAB]",
            "Delete"    : b"[DEL]",
            "Escape"    : b"[ESC]",
            "Up"        : b"[UP]",
            "Down"      : b"[DOWN]",
            "Left"      : b"[LEFT]",
            "Right"     : b"[RIGHT]",
            "Home"      : b"[HOME]",
            "End"       : b"[END]",
            "Prior"     : b"[PGUP]",
            "Next"      : b"[PGDN]",
        }

        try:
            if keysym in SPECIAL:
                self.serial_conn.write(SPECIAL[keysym] + b"\n")
                self._log(f"⚡ Sent: [{keysym}]")
            elif keysym == "space":
                self.serial_conn.write(b"[SPACE]\n")
                self._log("⚡ Sent: [SPACE]")
            elif char and len(char) == 1 and 32 <= ord(char) <= 126:
                self.serial_conn.write(char.encode("ascii") + b"\n")
                self._log(f"⚡ Sent: {repr(char)}")
        except Exception as ex:
            self._log(f"Serial error: {ex}")

    # ── Port helpers ───────────────────────────────────────────────────────────
    def _build_port_display(self, p):
        """Return a human-readable label and the raw device for a port."""
        chip = ESP_VIDS.get(p.vid, None)
        if chip:
            label = f"★ {p.device} — {chip}"     # star = likely ESP32
        elif p.description and p.description.lower() != "n/a":
            label = f"  {p.device} — {p.description}"
        else:
            label = f"  {p.device}"
        return label, p.device

    def _refresh_ports(self):
        ports = list(serial.tools.list_ports.comports())
        self._port_map = {}
        display_list   = []

        for p in ports:
            label, device = self._build_port_display(p)
            self._port_map[label] = device
            display_list.append(label)

        self.port_cb["values"] = display_list

        if display_list:
            # prefer a starred (ESP32) port if present
            esp_entries = [l for l in display_list if l.startswith("★")]
            self.port_var.set(esp_entries[0] if esp_entries else display_list[0])
            self._log(f"Found {len(ports)} port(s).  ★ = likely ESP32")
        else:
            self.port_var.set("")
            self._log("No COM ports found. Plug in ESP32.")

        self.chip_var.set("")

    def _auto_detect(self):
        """Scan for first ESP32 VID, select it in dropdown, show chip info."""
        self._refresh_ports()
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            if p.vid in ESP_VIDS:
                chip_name = ESP_VIDS[p.vid]
                # find matching label in dropdown
                for label, device in self._port_map.items():
                    if device == p.device:
                        self.port_var.set(label)
                        break
                vid_str = f"0x{p.vid:04X}" if p.vid else "N/A"
                pid_str = f"0x{p.pid:04X}" if p.pid else "N/A"
                info = (f"⚡ Auto-detected: {p.device}  |  Chip: {chip_name}  |  "
                        f"VID: {vid_str}  PID: {pid_str}  |  S/N: {p.serial_number or 'N/A'}")
                self.chip_var.set(info)
                self._log(f"ESP32 found → {p.device} ({chip_name})")
                return

        # nothing found
        self.chip_var.set("")
        messagebox.showinfo(
            "Auto-detect",
            "No ESP32 found.\n\n"
            "Checked VIDs: CP2102 (0x10C4), CH340 (0x1A86), "
            "ESP32-S3 Native (0x303A), FTDI (0x0403).\n\n"
            "Try: replug cable, install CH340 / CP2102 driver, "
            "or select port manually."
        )
        self._log("Auto-detect: no ESP32 VID matched.")

    # ── Serial ─────────────────────────────────────────────────────────────────
    def _resolve_port(self):
        """Convert display label → actual device path."""
        selected = self.port_var.get()
        return self._port_map.get(selected, selected.strip())

    def _connect(self):
        port = self._resolve_port()
        if not port:
            messagebox.showwarning("No Port", "Select a COM port first.")
            return
        try:
            self.serial_conn = serial.Serial(port, 115200, timeout=1)
            self.status_dot.configure(text=f"●  {port}", fg=GREEN)
            # show chip info for connected port if known
            for p in serial.tools.list_ports.comports():
                if p.device == port and p.vid in ESP_VIDS:
                    self.chip_var.set(
                        f"Connected  |  {ESP_VIDS[p.vid]}  |  "
                        f"VID: 0x{p.vid:04X}  PID: 0x{p.pid:04X}"
                    )
                    break
            self._log(f"Connected to {port} @ 115200 baud.")
        except Exception as ex:
            messagebox.showerror("Connection Error", str(ex))

    def _disconnect(self):
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        self.serial_conn = None
        self.chip_var.set("")
        self.status_dot.configure(text="●  DISCONNECTED", fg=RED)
        self._log("Disconnected.")

    # ── Delay ──────────────────────────────────────────────────────────────────
    def _delay_up(self):
        self.delay_var.set(min(500, self.delay_var.get() + 10))

    def _delay_down(self):
        self.delay_var.set(max(10, self.delay_var.get() - 10))

    # ── Batch actions ──────────────────────────────────────────────────────────
    def _paste(self):
        try:
            text = self.root.clipboard_get()
            self.editor.insert("end", text)
            self._update_lines()
            self._log(f"Pasted {len(text)} characters.")
        except Exception:
            self._log("Clipboard is empty or unavailable.")

    def _clear(self):
        self.editor.delete("1.0", "end")
        self.progress_var.set(0)
        self.prog_label.configure(text="0 / 0 chars")
        self._update_lines()
        self._log("Editor cleared.")

    def _start_typing(self):
        if self.is_typing:
            return
        if not self.serial_conn or not self.serial_conn.is_open:
            messagebox.showwarning("Not Connected", "Connect to ESP32 first.")
            return
        text = self.editor.get("1.0", "end-1c")
        if not text.strip():
            messagebox.showwarning("Empty", "Nothing to type.")
            return
        self.is_typing = True
        self.type_btn.configure(bg="#333")
        threading.Thread(target=self._type_worker, args=(text,), daemon=True).start()

    def _type_worker(self, text):
        total = len(text)
        self._log(f"Typing {total} characters...")
        for i, char in enumerate(text):
            try:
                # Keep batch mode protocol identical to live mode token encoding.
                if char == "\n":
                    self.serial_conn.write(b"[ENTER]\n")
                elif char == " ":
                    self.serial_conn.write(b"[SPACE]\n")
                elif 32 <= ord(char) <= 126:
                    self.serial_conn.write(char.encode("ascii") + b"\n")
            except Exception as ex:
                self._log(f"Serial error: {ex}")
                break
            self.root.after(0, self.progress_var.set, min(100, (i + 1) / total * 100))
            self.root.after(0, self.prog_label.configure,
                            {"text": f"{i + 1} / {total} chars"})
            # Delay is applied per transmitted character.
            time.sleep(self.delay_var.get() / 1000)
        self.root.after(0, self._typing_done)

    def _typing_done(self):
        self.is_typing = False
        self.progress_var.set(100)
        self._log("✓ Done typing!")
        self.type_btn.configure(bg=GREEN)
        self.root.after(2000, lambda: self.progress_var.set(0))

    def _log(self, msg):
        self.log_var.set(f"● {msg}")


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app  = ESP32KeyboardSender(root)
    root.mainloop()