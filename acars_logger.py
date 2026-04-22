#!/usr/bin/env python3
#
# acars-pi-dashboard — acars_logger.py
# Captures acarsdec JSON output and stores messages in per-day SQLite databases
#
# Project : https://github.com/anthonyborriello/acars-pi-dashboard
# Author  : Antonio Borriello
# License : MIT
#
# Built on top of:
#   acarsdec  by Thierry Leconte  — https://github.com/TLeconte/acarsdec
#   libacars  by Tomasz Duda     — https://github.com/szpajder/libacars
#
import subprocess
import sqlite3
import json
import os
import sys
from datetime import datetime, timezone

LOGS_DIR = "/home/pi/acars_logs"
ACARSDEC = "/usr/local/bin/acarsdec"
FREQ     = ["131.725", "131.825"]

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
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
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tail  ON messages(tail)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ts    ON messages(ts)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_label ON messages(label)")
    conn.commit()
    return conn

def get_db():
    today   = datetime.now(timezone.utc).strftime("%Y_%m_%d")
    db_path = os.path.join(LOGS_DIR, f"acars_{today}.db")
    return init_db(db_path), today

def save(conn, j):
    try:
        conn.execute(
            "INSERT INTO messages (freq,label,tail,flight,assstat,text,error,raw) VALUES (?,?,?,?,?,?,?,?)",
            (
                j.get("freq"),
                j.get("label", "").strip(),
                j.get("tail", ""),
                j.get("flight", ""),
                j.get("assstat", ""),
                j.get("text", j.get("txt", "")),
                j.get("error", 0),
                json.dumps(j),
            )
        )
        conn.commit()
    except Exception as e:
        now = datetime.now(timezone.utc)
        print(f"[{now} UTC] [DATABASE ERROR] {e}", file=sys.stderr)

def main():
    os.makedirs(LOGS_DIR, exist_ok=True)
    conn, current_day = get_db()
    now = datetime.now(timezone.utc)
    print(f"[{now} UTC] Logger started — saving to acars_{current_day}.db")

    proc = subprocess.Popen(
        [ACARSDEC, "--output", "json:file", "--rtlsdr", "0"] + FREQ,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    try:
        for line in proc.stdout:
            line = line.strip()
            if not line or line[0] != "{":
                continue
            try:
                j = json.loads(line)
                today_utc = datetime.now(timezone.utc).strftime("%Y_%m_%d")
                if today_utc != current_day:
                    conn.close()
                    conn, current_day = get_db()
                    print(f"[{datetime.now(timezone.utc)} UTC] Day rotated → acars_{current_day}.db")
                save(conn, j)
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"[{datetime.now(timezone.utc)} UTC] [PROCESS ERROR] {e}", file=sys.stderr)
    except KeyboardInterrupt:
        print(f"\n[{datetime.now(timezone.utc)} UTC] Shutting down…")
    finally:
        proc.terminate()
        conn.close()

if __name__ == "__main__":
    main()
