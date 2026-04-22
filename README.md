# ✈ acars-pi-dashboard

> A lightweight, real-time ACARS monitoring station — two Python files, zero complexity.

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.x-000000?style=flat-square&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-WAL-003B57?style=flat-square&logo=sqlite&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Raspberry%20Pi-C51A4A?style=flat-square&logo=raspberry-pi&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-00ff99?style=flat-square)

---

## What is this?

**acars-pi-dashboard** is a minimal, self-contained ACARS logging and live web dashboard system built around [acarsdec](https://github.com/f00b4r0/acarsdec).

No Docker. No Node.js. No message brokers. No configuration files. Just two Python scripts and a browser.

- `acars_logger.py` — captures JSON output from `acarsdec` and stores every message in a per-day SQLite database with WAL mode for safe concurrent access
- `acars_ui.py` — serves a real-time web dashboard via Flask, polling for new messages every 5 seconds with zero page reloads

Tested on **Raspberry Pi 2B** with **Debian Trixie**, but runs on any modern Linux system.

---

## Screenshots

<img width="1920" height="1080" alt="web page" src="https://github.com/user-attachments/assets/f59282ed-9dc9-4e21-95d3-60931e6ee94a" />
<br><br>
<img width="1920" height="1080" alt="web page 2" src="https://github.com/user-attachments/assets/e1cb0520-524b-4e8d-a567-1a57a32bd95b" />

---

## Features

- **Live dashboard** — new messages appear automatically every 5 seconds, no refresh needed
- **Color-coded rows** — ADS-C telemetry in blue, complete messages in white, errors in red, SQ squitter dimmed
- **ADS-C telemetry extraction** — latitude, longitude, altitude, ground speed, track, vertical speed decoded from ARINC-622 / libacars data
- **Per-day SQLite databases** — automatic UTC midnight rotation, historical day browsing via dropdown
- **Filtering** — filter by tail number, flight number, label type, and message status
- **SQ squitter toggle** — show/hide squitter messages on demand
- **Audio alerts** — optional sound notifications for new messages and squitter (Web Audio API, no dependencies)
- **Raw data endpoint** — `/raw` JSON endpoint for last 1000 messages per day (configurable up to 5000)
- **Connection lost indicator** — blinking red alert if the server becomes unreachable, auto-recovers
- **WAL mode SQLite** — logger writes and UI reads simultaneously with zero locking conflicts
- **Systemd ready** — designed to run as background services on boot

---

## Hardware

Tested with:

| Component | Model |
|-----------|-------|
| SBC | Raspberry Pi 2B |
| SDR Dongle | NooElec NESDR (RTL2832U) |
| Antenna | Diamond SRH789 |

Any RTL-SDR compatible dongle will work. For best results use a VHF antenna tuned for the 129–131 MHz airband.

---

## Requirements

### System dependencies

```bash
sudo apt install python3-flask
```

### libacars 

libacars enables full ADS-C and CPDLC decoding. Install it **before** compiling acarsdec.

```bash
sudo apt install cmake build-essential pkg-config
git clone https://github.com/szpajder/libacars.git
cd libacars && mkdir build && cd build
cmake .. && make && sudo make install && sudo ldconfig
cd ../..
```

### acarsdec (f00b4r0 fork)

This project uses the actively maintained fork by [f00b4r0](https://github.com/f00b4r0/acarsdec), which features automatic library autodetection, optimized Raspberry Pi builds, and is actively maintained.

Install the required dependencies, clone and build: (Use the cmake flag that matches your Raspberry Pi model)

```bash
sudo apt install librtlsdr-dev libcjson-dev
git clone https://github.com/f00b4r0/acarsdec.git
cd acarsdec && mkdir build && cd build
cmake .. -DCMAKE_C_FLAGS="-mcpu=cortex-a7 -mfpu=neon-vfpv4"
make && sudo make install
```

| Model | Flag |
|-------|------|
| Pi 2B | `-DCMAKE_C_FLAGS="-mcpu=cortex-a7 -mfpu=neon-vfpv4"` |
| Pi 3B | `-DCMAKE_C_FLAGS="-mcpu=cortex-a53 -mfpu=neon-fp-armv8"` |
| Pi 4B | `-DCMAKE_C_FLAGS="-mcpu=cortex-a72 -mfpu=neon-fp-armv8"` |
| Other Linux | `-DCMAKE_C_FLAGS="-march=native"` |

Verify the installation:

```bash
acarsdec --help
```

---

## Installation

```bash
git clone https://github.com/anthonyborriello/acars-pi-dashboard.git
cd acars-pi-dashboard
sudo apt install python3-flask
```

---

## Configuration

Edit the top of each file to match your setup:

### `acars_logger.py`

```python
LOGS_DIR = "/home/pi/acars_logs"       # where databases are stored
ACARSDEC = "/usr/local/bin/acarsdec"   # path to acarsdec binary
FREQ     = ["131.725", "131.825"]      # frequencies to monitor (MHz)
```

### `acars_ui.py`

```python
LOGS_DIR = "/home/pi/acars_logs"       # must match logger path
```

> **Frequencies:** The values above are typical for Europe. Adjust for your region — check [airframes.io](https://app.airframes.io/about) for frequencies active in your area. Note that all frequencies must fall within the same 2 MHz window for a single RTL-SDR dongle.

---

## Usage

### Manual start

Open two terminals (or use `tmux` / `screen`):

```bash
# Terminal 1 — start the logger
python3 acars_logger.py

# Terminal 2 — start the web UI
python3 acars_ui.py
```

Then open your browser at:

```
http://<your-pi-ip>:5000
```

---

## Running as systemd services

Create the logger service:

```bash
sudo nano /etc/systemd/system/acars-logger.service
```

```ini
[Unit]
Description=ACARS Logger
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/acars-pi-dashboard/acars_logger.py
WorkingDirectory=/home/pi/acars-pi-dashboard
Restart=always
RestartSec=5
User=pi

[Install]
WantedBy=multi-user.target
```

Create the UI service:

```bash
sudo nano /etc/systemd/system/acars-ui.service
```

```ini
[Unit]
Description=ACARS Web Dashboard
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/acars-pi-dashboard/acars_ui.py
WorkingDirectory=/home/pi/acars-pi-dashboard
Restart=always
RestartSec=5
User=pi

[Install]
WantedBy=multi-user.target
```

Enable and start both services:

```bash
sudo systemctl daemon-reload
sudo systemctl enable acars-logger acars-ui
sudo systemctl start acars-logger acars-ui
```

Check status:

```bash
sudo systemctl status acars-logger
sudo systemctl status acars-ui
```

---

## Alternative: start on boot with crontab

If you prefer a simpler approach over systemd, you can use `crontab -e`.

First, make sure the log directory exists. While you are in your home directory, run:

```bash
mkdir -p /home/pi/acars_logs
```

Then open the crontab editor:

```bash
crontab -e
```

Add these two lines at the bottom:

```
@reboot sleep 60 && /usr/bin/python3 -u /home/pi/acars-pi-dashboard/acars_logger.py >> /home/pi/acars_logs/logger.log 2>&1
@reboot sleep 70 && /usr/bin/python3 /home/pi/acars-pi-dashboard/acars_ui.py >> /dev/null 2>&1
```

The `sleep 60/70` gives the system time to fully initialize before starting (network, USB dongle, etc.). The `-u` flag on the logger disables Python output buffering so log entries appear immediately. The `>> ... 2>&1` redirects stdout and stderr to a log file — useful for debugging.

---

## Dashboard overview

| Column | Description |
|--------|-------------|
| Time | UTC timestamp of the message |
| Freq | Receiving frequency in MHz |
| Label | ACARS label code (e.g. H1, B2, SQ) |
| Tail | Aircraft registration |
| Flight | Flight number |
| Blk | Block ID |
| Msg# | Message number |
| Status | Assembly status: `[FULL]` / `[...]` / `[OOS]` |
| Text | Decoded message content |
| Lat / Lon / Alt | Position data from ADS-C (when available) |
| GS/TRK/VS | Ground speed (kts), track (°), vertical speed (ft/min) |

### Row colors

| Color | Meaning |
|-------|---------|
| 🟦 Blue | ADS-C message with position data |
| ⬜ White | Complete assembled message |
| 🟥 Red | Message with decode error |
| ⬛ Dim green | SQ squitter (hidden by default) |
| ▪ Grey | General message |

---

## Database structure

Each day generates a file: `acars_YYYY_MM_DD.db`

```
/home/pi/acars_logs/
├── acars_2026_04_21.db
├── acars_2026_04_21.db-wal    ← WAL journal (normal, safe)
├── acars_2026_04_21.db-shm    ← shared memory (normal, safe)
└── acars_2026_04_22.db
```

The `.db-wal` and `.db-shm` files are part of SQLite's **Write-Ahead Logging** mechanism. They allow the logger to write and the UI to read simultaneously without locking conflicts. They are safe and expected — do not delete them while the logger is running.

Databases rotate automatically at **UTC midnight**.

### Schema

```sql
CREATE TABLE messages (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ts      DATETIME DEFAULT CURRENT_TIMESTAMP,
    freq    REAL,
    label   TEXT,
    tail    TEXT,
    flight  TEXT,
    assstat TEXT,
    text    TEXT,
    error   INTEGER,
    raw     JSON
);
```

The `raw` column stores the complete original JSON from `acarsdec`, including full `libacars` decoded data where available.

---

## API endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Main dashboard (accepts `day`, `tail`, `flight`, `label`, `assstat` params) |
| `GET /api/new?day=&last_id=` | Poll for new messages + updated stats (used by the dashboard) |
| `GET /raw?day=&limit=` | Raw messages as JSON — default 1000, max 5000 (e.g. `/raw?day=2026_04_22&limit=3000`) |

---

## Design philosophy

Most ACARS web interfaces are either heavy Docker stacks or decade-old CGI scripts. This project sits in the middle: production-quality engineering with the smallest possible footprint.

Key decisions:

- **WAL mode SQLite** — concurrent read/write without locking; sequential writes are gentler on SD cards than random writes
- **Single poll endpoint** — `/api/new` returns both new messages and updated stats in one HTTP call, halving network overhead vs. a separate `/api/stats`
- **Server-side enrichment** — CSS classes, status strings, and telemetry are computed once in Python (`enrich()`), never duplicated in JavaScript
- **No build step** — pure HTML/CSS/JS served inline via Flask's `render_template_string`; no npm, no webpack, no transpilation
- **UTC timestamps everywhere** — databases rotate at UTC midnight; timestamps stored and displayed in UTC

---

## Compatibility

| System | Status |
|--------|--------|
| Raspberry Pi 2B + Debian Trixie | ✅ Tested |
| Raspberry Pi OS (Bookworm) | ✅ Expected to work |
| Ubuntu 22.04 / 24.04 | ✅ Expected to work |
| Any modern Linux + Python 3.8+ | ✅ Should work |
| Windows / macOS | ❌ Not supported (acarsdec is Linux-only) |

---

## Tips

**Finding your ACARS frequencies:**
Visit [airframes.io](https://app.airframes.io/about) to find which frequencies are most active in your region before configuring `FREQ`.

**Antenna matters more than gain:**
A proper VHF antenna (like the Diamond SRH789) will outperform a telescopic whip with maximum gain. Avoid cranking RTL-SDR gain to maximum — it often increases noise more than signal.

**SD card longevity:**
WAL mode already helps by batching writes. For even better SD card protection, consider mounting `acars_logs` on a USB drive instead of the SD card root filesystem.

**Viewing old data:**
Use the day dropdown in the top-left of the dashboard to browse historical databases. The UI is read-only for past days — live polling only activates for today's date.

**Multiple instances:**
Only one instance of `acars_logger.py` can run at a time — acarsdec will fail to open the dongle if another instance is already using it. If the logger exits immediately, check for stale processes with `ps aux | grep acarsdec`.

---

## Contributing

Pull requests are welcome. If you test on a new platform or hardware combination, please open an issue or PR to update the compatibility table.

---

## Credits

- [acarsdec](https://github.com/f00b4r0/acarsdec) fork by Thibaut Varène (f00b4r0) — actively maintained decoder, recommended
- [acarsdec](https://github.com/TLeconte/acarsdec) original by Thierry Leconte — the decoder that started it all
- [libacars](https://github.com/szpajder/libacars) by Tomasz Duda — ADS-C / CPDLC decoding library
- [airframes.io](https://app.airframes.io) — community ACARS message reference

---

## License

MIT License — free to use, modify, and distribute.

