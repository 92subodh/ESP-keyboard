# ◈ ESP32 BLE Keyboard Sender

A PC application that turns your ESP32 into a wireless BLE keyboard. Type or paste text on your PC and it gets sent character-by-character to any BLE-connected device (phone, tablet, smart TV, etc.).

---

## 📁 Project Files

| File | Description |
|------|-------------|
| `esp32_ble_keyboard.ino` | Arduino sketch — upload this to your ESP32 |
| `sender.py` | Python desktop app — run this on your PC |

---

## 🔧 Requirements

### 1. CP210x USB-to-UART Driver (ESSENTIAL — Install First)

Most ESP32 dev boards use a **Silicon Labs CP2102** chip for USB communication. Without this driver Windows/macOS will not recognise the board.

**Windows:**
- Download from: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
- Choose **CP210x Universal Windows Driver**
- Extract the ZIP → right-click `silabser.inf` → **Install**
- Or run the `.exe` installer if provided
- After installing, plug in ESP32 → Device Manager should show `Silicon Labs CP210x USB to UART Bridge (COMx)`

**macOS:**
- Download the macOS VCP driver from the same Silicon Labs page
- Open the `.dmg` → run the `.pkg` installer
- Go to **System Preferences → Security & Privacy** and allow the driver if prompted
- Reboot recommended

**Linux:**
- The `cp210x` module is built into most kernels — no install needed
- Plug in ESP32 and run: `ls /dev/ttyUSB*` — you should see `/dev/ttyUSB0`
- If permission denied: `sudo usermod -aG dialout $USER` then log out and back in

> ⚠️ Some boards use a **CH340/CH341** chip instead of CP2102. If COM port still doesn't appear after installing CP210x drivers, install the CH340 driver from: https://www.wch-ic.com/downloads/CH341SER_EXE.html

---

### 2. Arduino IDE + ESP32 Board Support

**Install Arduino IDE:**
- Download from: https://www.arduino.cc/en/software
- Version 2.x recommended

**Add ESP32 board support:**
1. Open Arduino IDE → **File → Preferences**
2. In *Additional Boards Manager URLs* paste:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. Go to **Tools → Board → Boards Manager**
4. Search `esp32` → Install **esp32 by Espressif Systems**

---

### 3. Arduino Library — ESP32 BLE Keyboard

1. In Arduino IDE go to **Sketch → Include Library → Manage Libraries**
2. Search: `ESP32 BLE Keyboard`
3. Install **ESP32 BLE Keyboard by T-vK**

Or install manually:
- Download ZIP from: https://github.com/T-vK/ESP32-BLE-Keyboard
- Arduino IDE → **Sketch → Include Library → Add .ZIP Library**

---

### 4. Python Dependencies

Requires **Python 3.7+**. Install the two required packages:

```bash
pip install pyserial
```

> `tkinter` is included with standard Python on Windows and macOS.
> On Linux if tkinter is missing: `sudo apt install python3-tk`

---

## 🚀 Setup & Usage

### Step 1 — Upload the Arduino Sketch

1. Open `esp32_ble_keyboard.ino` in Arduino IDE
2. Go to **Tools → Board** → select your ESP32 board
   - Most common: `ESP32 Dev Module`
3. Go to **Tools → Port** → select the COM port your ESP32 is on
4. Click **Upload** (→ arrow button)
5. Open Serial Monitor (baud: 115200) — you should see:
   ```
   BLE Keyboard ready. Waiting for connection...
   ```

### Step 2 — Pair ESP32 as a Bluetooth Keyboard

1. On your target device (phone, tablet, PC) open **Bluetooth Settings**
2. Scan for new devices — look for **"ESP32 Keyboard"**
3. Tap/click to pair — no PIN needed
4. The Serial Monitor will show the BLE connection status

### Step 3 — Run the Python App

```bash
python sender.py
```

1. Click **⟳ REFRESH** to scan for COM ports
2. Select the ESP32's COM port from the dropdown
3. Click **CONNECT** — status dot turns green
4. Choose your mode (see below) and start sending text

---

## ⚡ Modes

### LIVE Mode
Every key you press in the editor is sent to the ESP32 instantly in real time. Useful for navigating menus or typing short inputs on the target device.

Supported special keys: `Enter`, `Backspace`, `Tab`, `Delete`, `Escape`, `Arrow keys`, `Home`, `End`, `Page Up`, `Page Down`, `Space`

### BATCH Mode
Type or paste your full text in the editor, set the character delay with the slider, then click **▶ START TYPING**. The app sends one character at a time at the chosen speed.

- **FAST 20ms** — quick typing, may miss chars on slow targets
- **NORMAL 50ms** — reliable for most devices
- **SLOW 150ms** — for older or laggy Bluetooth targets

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---------|-----|
| No COM ports found | Install CP210x or CH340 driver; replug ESP32 |
| COM port found but can't connect | Another app (Serial Monitor) is using the port — close it |
| BLE device not appearing | Press reset button on ESP32; ensure BLE is enabled on target |
| Characters missing in BATCH | Increase delay with the slider |
| Space not working (LIVE mode) | Ensure you have applied the `[SPACE]` fix in both files |
| Upload fails in Arduino IDE | Hold the **BOOT** button on ESP32 while clicking Upload, release after upload starts |

---

## 📐 How It Works

```
PC keyboard / paste
       ↓
  sender.py (Python)
       ↓  USB Serial (115200 baud)
  ESP32 Arduino sketch
       ↓  Bluetooth Low Energy (BLE HID)
  Target device (phone / tablet / PC)
```

The Python app sends characters as ASCII over USB serial. The ESP32 receives them and re-emits them as standard BLE HID keyboard events — the target device sees it as a real keyboard.

---

## 📦 Dependencies Summary

| Component | What | Where |
|-----------|------|--------|
| CP210x Driver | USB-Serial bridge | silabs.com |
| Arduino IDE 2.x | Upload tool | arduino.cc |
| ESP32 Board Package | Board support | Boards Manager (Espressif) |
| ESP32 BLE Keyboard lib | BLE HID | Library Manager (T-vK) |
| Python 3.7+ | Run the PC app | python.org |
| pyserial | Serial comms | `pip install pyserial` |
| tkinter | GUI (built-in) | Included with Python |